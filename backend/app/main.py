"""ORAC-FloodGuard FastAPI Application Entrypoint."""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.core.config import settings
from backend.app.core.logging import setup_logging, logger
from backend.app.core.exceptions import FloodGuardException
from backend.app.api.routes import (
    health,
    flood,
    agents,
    weather,
    river,
    dam,
    gis,
    evacuation,
    replay,
    reports,
    alerts,
)

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    logger.info("Initializing ORAC-FloodGuard Backend...")
    logger.info("Configuration: ENV=%s, DB_MODE=%s, LLM=%s",
                settings.APP_ENV, settings.DATABASE_MODE, settings.LLM_PROVIDER)
    try:
        from backend.app.database.init_db import init_db
        init_db()
    except Exception as e:
        logger.error("Failed to verify/migrate database schema on startup: %s", str(e))
    yield
    logger.info("Shutting down ORAC-FloodGuard Backend...")


app = FastAPI(
    title=f"{settings.APP_NAME} API",
    description="Agentic AI-powered Flood Early-Warning and Village Evacuation Advisor for Punjab, India",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware for React frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(FloodGuardException)
async def floodguard_exception_handler(request: Request, exc: FloodGuardException):
    """Handle custom application exceptions."""
    logger.error("FloodGuardException on %s: %s (details: %s)",
                 request.url.path, exc.message, exc.details)
    return JSONResponse(
        status_code=400,
        content={"detail": exc.message, "details": exc.details},
    )


# Register all API endpoints
prefix = settings.API_V1_PREFIX
app.include_router(health.router, prefix=prefix)
app.include_router(flood.router, prefix=prefix)
app.include_router(agents.router, prefix=prefix)
app.include_router(weather.router, prefix=prefix)
app.include_router(river.router, prefix=prefix)
app.include_router(dam.router, prefix=prefix)
app.include_router(gis.router, prefix=prefix)
app.include_router(evacuation.router, prefix=prefix)
app.include_router(replay.router, prefix=prefix)
app.include_router(reports.router, prefix=prefix)
app.include_router(alerts.router, prefix=prefix)


@app.get("/")
def root():
    """Root redirect / information."""
    return {
        "message": "Welcome to ORAC-FloodGuard API",
        "docs": "/docs",
        "health": f"{settings.API_V1_PREFIX}/health",
    }
