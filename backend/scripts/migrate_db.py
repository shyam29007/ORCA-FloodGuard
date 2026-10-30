"""CLI migration runner script for ORAC-FloodGuard."""

import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
root_dir = backend_dir.parent
for p in [str(backend_dir), str(root_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from backend.app.database.connection import engine
from backend.app.database.migration import run_database_migrations, migrate_sqlite_file
from backend.app.core.logging import logger
import os


def main():
    print("=" * 60)
    print("ORAC-FloodGuard: Database Schema Migration Runner")
    print("=" * 60)

    # 1. Run via configured SQLAlchemy engine
    print(f"Connecting to database: {engine.url}...")
    applied = run_database_migrations(engine)
    if applied:
        print(f"Applied {len(applied)} migrations successfully:")
        for s in applied:
            print(f"  + {s}")
    else:
        print("Database schema is already up to date.")

    # 2. Check and migrate local sqlite file if present
    for db_file in ["orac_floodguard.db", "backend/orac_floodguard.db"]:
        if os.path.exists(db_file):
            print(f"\nChecking local SQLite file: {db_file}...")
            f_applied = migrate_sqlite_file(db_file)
            if f_applied:
                print(f"  Applied to {db_file}: {f_applied}")
            else:
                print(f"  {db_file} is up to date.")

    print("\nMigration completed successfully.")


if __name__ == "__main__":
    main()

