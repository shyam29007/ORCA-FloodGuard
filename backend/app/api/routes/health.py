"""Health and readiness check endpoints."""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.app.api.dependencies import get_db
from backend.app.core.config import settings

router = APIRouter(tags=["Health"])


@router.get("/health")
def get_health(db: Session = Depends(get_db)):
    """Health check endpoint validating database connectivity and system status."""
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    llm_prov = settings.LLM_PROVIDER or "gemini"
    llm_model = settings.LLM_MODEL if settings.LLM_MODEL else "NOT_CONFIGURED"
    if llm_prov == "gemini":
        is_key_present = bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip())
    elif llm_prov == "openai":
        is_key_present = bool(settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.strip())
    elif llm_prov == "mock":
        is_key_present = True
    else:
        is_key_present = False

    llm_config_status = "CONFIGURED" if (is_key_present and settings.LLM_MODEL) else "NOT_CONFIGURED"

    return {
        "status": "healthy" if "unhealthy" not in db_status else "degraded",
        "app_status": "APPLICATION ONLINE",
        "telemetry_health": "TELEMETRY DISCONNECTED (Awaiting Official Credentials)",
        "database_health": "DATABASE CONNECTED" if "unhealthy" not in db_status else "DATABASE UNHEALTHY",
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "database_mode": settings.DATABASE_MODE,
        "database_status": db_status,
        "llm_provider": llm_prov,
        "llm_model_id": llm_model,
        "llm_configuration_status": llm_config_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
    }
