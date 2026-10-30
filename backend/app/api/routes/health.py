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

    return {
        "status": "healthy" if "unhealthy" not in db_status else "degraded",
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "database_mode": settings.DATABASE_MODE,
        "database_status": db_status,
        "llm_provider": settings.LLM_PROVIDER,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
    }

