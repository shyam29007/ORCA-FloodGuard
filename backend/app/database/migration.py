"""SQLite & PostgreSQL database schema migration engine for ORCA-FloodGuard.

Safely adds missing columns, removes outdated NOT NULL constraints,
tracks versioned migrations, and preserves existing data.
"""

from datetime import datetime, timezone
import sqlite3
from typing import List, Dict, Any, Tuple, Callable
from sqlalchemy import Engine, inspect, text
from backend.app.core.logging import logger


MIGRATIONS: List[Dict[str, Any]] = [
    {
        "version": "2026_10_30_001_safety_validation_fields",
        "name": "Add confidence_status, validation, mode and audit json columns",
        "kind": "add_columns",
        "columns": [
            # (table_name, column_name, sql_type, default_clause)
            ("flood_assessments", "confidence_status", "VARCHAR(50)", "DEFAULT 'NOT_CALIBRATED'"),
            ("flood_assessments", "schema_validation_status", "VARCHAR(50)", "DEFAULT 'PASSED'"),
            ("flood_assessments", "evidence_sufficiency_status", "VARCHAR(50)", "DEFAULT 'SUFFICIENT'"),
            ("flood_assessments", "assessment_mode", "VARCHAR(50)", "DEFAULT 'OPERATIONAL'"),
            ("flood_assessments", "assessment_status", "VARCHAR(50)", "DEFAULT 'OPERATIONAL'"),
            ("flood_assessments", "limitations_json", "JSON", "DEFAULT '[]'"),
            ("flood_assessments", "warnings_json", "JSON", "DEFAULT '[]'"),
            ("flood_assessments", "excluded_evidence_json", "JSON", "DEFAULT '[]'"),
            ("village_risk_outlooks", "confidence_status", "VARCHAR(50)", "DEFAULT 'NOT_CALIBRATED'"),
            ("village_risk_outlooks", "confidence_score", "FLOAT", "DEFAULT NULL"),
            ("village_risk_outlooks", "supporting_evidence_ids_json", "JSON", "DEFAULT '[]'"),
        ],
    },
    {
        "version": "2026_10_30_002_nullable_confidence_score",
        "name": "Remove NOT NULL constraint from confidence_score and confidence columns",
        "kind": "remove_not_null",
    },
]


def ensure_migration_table(connection: Any) -> None:
    """Ensure the schema_migrations tracking table exists."""
    create_sql = """
    CREATE TABLE IF NOT EXISTS schema_migrations (
        version VARCHAR(100) PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        applied_at DATETIME NOT NULL
    );
    """
    if hasattr(connection, "exec_driver_sql"):
        connection.exec_driver_sql(create_sql)
    elif hasattr(connection, "execute"):
        connection.execute(text(create_sql))


def get_applied_migrations(connection: Any) -> List[str]:
    """Get list of already-applied migration versions."""
    ensure_migration_table(connection)
    query = "SELECT version FROM schema_migrations;"
    if hasattr(connection, "exec_driver_sql"):
        result = connection.exec_driver_sql(query)
        return [row[0] for row in result.fetchall()]
    elif hasattr(connection, "execute"):
        result = connection.execute(text(query))
        return [row[0] for row in result.fetchall()]
    return []


def record_migration_applied(connection: Any, version: str, name: str) -> None:
    """Record that a migration version has been successfully applied."""
    now_iso = datetime.now(timezone.utc).isoformat()
    insert_sql = "INSERT INTO schema_migrations (version, name, applied_at) VALUES (:version, :name, :applied_at);"
    if hasattr(connection, "exec_driver_sql"):
        connection.exec_driver_sql(
            "INSERT INTO schema_migrations (version, name, applied_at) VALUES (?, ?, ?);",
            (version, name, now_iso),
        )
    elif hasattr(connection, "execute"):
        connection.execute(
            text(insert_sql),
            {"version": version, "name": name, "applied_at": now_iso},
        )


def get_sqlite_table_columns(connection: Any, table_name: str) -> List[str]:
    """Return list of existing column names for an SQLite table."""
    pragma_sql = f"PRAGMA table_info({table_name});"
    if hasattr(connection, "exec_driver_sql"):
        res = connection.exec_driver_sql(pragma_sql)
        return [row[1] for row in res.fetchall()]
    elif hasattr(connection, "execute"):
        res = connection.execute(text(pragma_sql))
        return [row[1] for row in res.fetchall()]
    return []


def remove_sqlite_not_null_constraints(
    execute_fn: Callable[[str], Any],
    query_fn: Callable[[str], List[Tuple[Any, ...]]],
) -> List[str]:
    """Safely rebuild SQLite tables to drop NOT NULL constraint on confidence columns.

    Preserves existing records, indices, foreign keys, and defaults.
    """
    applied: List[str] = []
    tables = [r[0] for r in query_fn("SELECT name FROM sqlite_master WHERE type='table';")]
    if "flood_assessments" not in tables:
        return applied

    fa_info = query_fn("PRAGMA table_info(flood_assessments);")
    cs_col = next((c for c in fa_info if c[1] == "confidence_score"), None)
    rebuild_fa = cs_col is not None and cs_col[3] == 1  # notnull == 1

    vo_info = query_fn("PRAGMA table_info(village_risk_outlooks);") if "village_risk_outlooks" in tables else []
    conf_col = next((c for c in vo_info if c[1] == "confidence"), None)
    rebuild_vo = conf_col is not None and conf_col[3] == 1  # notnull == 1

    if not rebuild_fa and not rebuild_vo:
        return applied

    execute_fn("PRAGMA foreign_keys = OFF;")

    if rebuild_fa:
        logger.info("Rebuilding flood_assessments to remove NOT NULL from confidence_score...")
        execute_fn("""
        CREATE TABLE new_flood_assessments (
            id VARCHAR(36) NOT NULL PRIMARY KEY,
            run_id VARCHAR(64) NOT NULL,
            village_id VARCHAR(36) NOT NULL,
            overall_risk VARCHAR(30) NOT NULL,
            confidence_score FLOAT,
            confidence_status VARCHAR(50) DEFAULT 'NOT_CALIBRATED',
            validation_status VARCHAR(50) NOT NULL DEFAULT 'PASSED',
            schema_validation_status VARCHAR(50) DEFAULT 'PASSED',
            evidence_sufficiency_status VARCHAR(50) DEFAULT 'SUFFICIENT',
            assessment_mode VARCHAR(50) DEFAULT 'OPERATIONAL',
            assessment_status VARCHAR(50) DEFAULT 'OPERATIONAL',
            triggered_rules_json JSON,
            explanation TEXT NOT NULL,
            limitations_json JSON DEFAULT '[]',
            warnings_json JSON DEFAULT '[]',
            excluded_evidence_json JSON DEFAULT '[]',
            created_at DATETIME,
            updated_at DATETIME,
            FOREIGN KEY(village_id) REFERENCES villages (id) ON DELETE CASCADE
        );
        """)
        old_cols = [c[1] for c in fa_info]
        new_cols = [
            'id', 'run_id', 'village_id', 'overall_risk', 'confidence_score',
            'confidence_status', 'validation_status', 'schema_validation_status',
            'evidence_sufficiency_status', 'assessment_mode', 'assessment_status',
            'triggered_rules_json', 'explanation', 'limitations_json', 'warnings_json',
            'excluded_evidence_json', 'created_at', 'updated_at'
        ]
        common_cols = [c for c in new_cols if c in old_cols]
        cols_str = ", ".join(common_cols)
        execute_fn(f"INSERT INTO new_flood_assessments ({cols_str}) SELECT {cols_str} FROM flood_assessments;")
        execute_fn("DROP TABLE flood_assessments;")
        execute_fn("ALTER TABLE new_flood_assessments RENAME TO flood_assessments;")
        execute_fn("CREATE INDEX IF NOT EXISTS ix_flood_assessments_run_id ON flood_assessments (run_id);")
        execute_fn("CREATE INDEX IF NOT EXISTS ix_flood_assessments_village_id ON flood_assessments (village_id);")
        applied.append("Made flood_assessments.confidence_score nullable")
        logger.info("Successfully rebuilt flood_assessments with nullable confidence_score.")

    if rebuild_vo:
        logger.info("Rebuilding village_risk_outlooks to remove NOT NULL from confidence...")
        execute_fn("""
        CREATE TABLE new_village_risk_outlooks (
            id VARCHAR(36) NOT NULL PRIMARY KEY,
            assessment_id VARCHAR(36) NOT NULL,
            horizon VARCHAR(10) NOT NULL,
            risk_level VARCHAR(30) NOT NULL,
            confidence FLOAT,
            confidence_status VARCHAR(50) DEFAULT 'NOT_CALIBRATED',
            confidence_score FLOAT DEFAULT NULL,
            primary_factors_json JSON,
            triggered_rules_json JSON,
            supporting_evidence_ids_json JSON DEFAULT '[]',
            rainfall_forecast_mm FLOAT DEFAULT NULL,
            river_risk VARCHAR(30) DEFAULT 'NORMAL',
            dam_risk VARCHAR(30) DEFAULT 'NORMAL',
            created_at DATETIME,
            FOREIGN KEY(assessment_id) REFERENCES flood_assessments (id) ON DELETE CASCADE
        );
        """)
        old_cols_vo = [c[1] for c in vo_info]
        new_cols_vo = [
            'id', 'assessment_id', 'horizon', 'risk_level', 'confidence',
            'confidence_status', 'confidence_score', 'primary_factors_json',
            'triggered_rules_json', 'supporting_evidence_ids_json',
            'rainfall_forecast_mm', 'river_risk', 'dam_risk', 'created_at'
        ]
        common_cols_vo = [c for c in new_cols_vo if c in old_cols_vo]
        cols_str_vo = ", ".join(common_cols_vo)
        execute_fn(f"INSERT INTO new_village_risk_outlooks ({cols_str_vo}) SELECT {cols_str_vo} FROM village_risk_outlooks;")
        execute_fn("DROP TABLE village_risk_outlooks;")
        execute_fn("ALTER TABLE new_village_risk_outlooks RENAME TO village_risk_outlooks;")
        execute_fn("CREATE INDEX IF NOT EXISTS ix_village_risk_outlooks_assessment_id ON village_risk_outlooks (assessment_id);")
        applied.append("Made village_risk_outlooks.confidence nullable")
        logger.info("Successfully rebuilt village_risk_outlooks with nullable confidence.")

    fk_issues = query_fn("PRAGMA foreign_key_check;")
    if fk_issues:
        raise RuntimeError(f"Foreign key check failed after schema migration: {fk_issues}")

    execute_fn("PRAGMA foreign_keys = ON;")
    return applied


def run_database_migrations(engine: Engine) -> List[str]:
    """Inspect and safely apply all pending migrations against the given SQLAlchemy Engine.

    Returns list of applied migration summaries.
    """
    applied_summaries: List[str] = []
    
    with engine.begin() as conn:
        ensure_migration_table(conn)
        applied_versions = get_applied_migrations(conn)
        is_sqlite = engine.dialect.name == "sqlite"

        for migration in MIGRATIONS:
            version = migration["version"]
            name = migration["name"]
            kind = migration.get("kind", "add_columns")

            if kind == "add_columns":
                columns_to_add: List[Tuple[str, str, str, str]] = []
                for table_name, col_name, col_type, default_clause in migration["columns"]:
                    if is_sqlite:
                        existing_cols = get_sqlite_table_columns(conn, table_name)
                        if existing_cols and col_name not in existing_cols:
                            columns_to_add.append((table_name, col_name, col_type, default_clause))
                    else:
                        insp = inspect(engine)
                        existing_cols = [c["name"] for c in insp.get_columns(table_name)] if insp.has_table(table_name) else []
                        if existing_cols and col_name not in existing_cols:
                            columns_to_add.append((table_name, col_name, col_type, default_clause))

                if columns_to_add:
                    for table_name, col_name, col_type, default_clause in columns_to_add:
                        alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type} {default_clause};"
                        logger.info("[Migration %s] Adding missing column: %s.%s (%s %s)", version, table_name, col_name, col_type, default_clause)
                        if hasattr(conn, "exec_driver_sql"):
                            conn.exec_driver_sql(alter_sql)
                        else:
                            conn.execute(text(alter_sql))
                        applied_summaries.append(f"Added {table_name}.{col_name} ({col_type})")

            elif kind == "remove_not_null":
                if is_sqlite:
                    def _exec(sql: str) -> None:
                        conn.exec_driver_sql(sql)

                    def _query(sql: str) -> List[Tuple[Any, ...]]:
                        res = conn.exec_driver_sql(sql)
                        return [tuple(row) for row in res.fetchall()]

                    sub_applied = remove_sqlite_not_null_constraints(_exec, _query)
                    applied_summaries.extend(sub_applied)
                else:
                    # PostgreSQL
                    insp = inspect(engine)
                    if insp.has_table("flood_assessments"):
                        conn.execute(text("ALTER TABLE flood_assessments ALTER COLUMN confidence_score DROP NOT NULL;"))
                        applied_summaries.append("Postgres: dropped NOT NULL on flood_assessments.confidence_score")
                    if insp.has_table("village_risk_outlooks"):
                        conn.execute(text("ALTER TABLE village_risk_outlooks ALTER COLUMN confidence DROP NOT NULL;"))
                        applied_summaries.append("Postgres: dropped NOT NULL on village_risk_outlooks.confidence")

            if version not in applied_versions:
                record_migration_applied(conn, version, name)
                logger.info("[Migration %s] Marked as applied in schema_migrations.", version)

    return applied_summaries


def migrate_sqlite_file(db_path: str) -> List[str]:
    """Directly migrate a specific SQLite database file using raw sqlite3 connection."""
    applied: List[str] = []
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        
        # Ensure schema_migrations table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version VARCHAR(100) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            applied_at DATETIME NOT NULL
        );
        """)
        
        cur.execute("SELECT version FROM schema_migrations;")
        applied_versions = {row[0] for row in cur.fetchall()}

        for migration in MIGRATIONS:
            version = migration["version"]
            name = migration["name"]
            kind = migration.get("kind", "add_columns")

            if kind == "add_columns":
                for table_name, col_name, col_type, default_clause in migration["columns"]:
                    cur.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';")
                    if not cur.fetchone():
                        continue

                    cur.execute(f"PRAGMA table_info({table_name});")
                    existing_cols = {row[1] for row in cur.fetchall()}

                    if col_name not in existing_cols:
                        alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type} {default_clause};"
                        cur.execute(alter_sql)
                        applied.append(f"{table_name}.{col_name}")
                        logger.info("[Direct SQLite Migrate %s] Executed: %s", db_path, alter_sql)

            elif kind == "remove_not_null":
                def _exec(sql: str) -> None:
                    cur.execute(sql)

                def _query(sql: str) -> List[Tuple[Any, ...]]:
                    cur.execute(sql)
                    return [tuple(r) for r in cur.fetchall()]

                sub_applied = remove_sqlite_not_null_constraints(_exec, _query)
                applied.extend(sub_applied)

            if version not in applied_versions:
                now_iso = datetime.now(timezone.utc).isoformat()
                cur.execute(
                    "INSERT INTO schema_migrations (version, name, applied_at) VALUES (?, ?, ?);",
                    (version, name, now_iso),
                )

        conn.commit()
    finally:
        conn.close()

    return applied
