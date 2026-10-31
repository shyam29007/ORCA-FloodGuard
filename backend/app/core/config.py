"""Core application configuration using Pydantic Settings."""

import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application settings loaded from environment or defaults."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # General
    APP_ENV: str = "development"
    APP_NAME: str = "ORCA-FloodGuard"
    API_V1_PREFIX: str = "/api"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    REQUEST_TIMEOUT: int = 20

    # Database
    DATABASE_MODE: str = "sqlite"  # 'sqlite' or 'postgres'
    DATABASE_URL: str = "sqlite:///./orca_floodguard.db"

    # LLM Settings (One shared provider configuration)
    LLM_PROVIDER: str = "gemini"  # 'gemini', 'openai', 'mock'
    LLM_MODEL: str = "gemini-1.5-flash"
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None

    # External Provider Base URLs
    WEATHER_API_BASE_URL: Optional[str] = None
    RIVER_API_BASE_URL: Optional[str] = None
    DAM_API_BASE_URL: Optional[str] = None
    ELEVATION_API_BASE_URL: Optional[str] = None
    IMD_API_KEY: Optional[str] = None
    CWC_API_KEY: Optional[str] = None
    BBMB_API_KEY: Optional[str] = None
    PROVIDER_MAX_RETRIES: int = 3
    PROVIDER_RETRY_BACKOFF_FACTOR: float = 0.5
    PROVIDER_MAX_BACKOFF_SECONDS: float = 4.0

    # Configurable Deterministic Risk Thresholds (Assumption baselines)
    RAIN_MODERATE_24H_MM: float = 40.0
    RAIN_HIGH_24H_MM: float = 75.0
    RAIN_CRITICAL_24H_MM: float = 120.0

    RAIN_MODERATE_48H_MM: float = 70.0
    RAIN_HIGH_48H_MM: float = 130.0
    RAIN_CRITICAL_48H_MM: float = 200.0

    RAIN_MODERATE_72H_MM: float = 100.0
    RAIN_HIGH_72H_MM: float = 180.0
    RAIN_CRITICAL_72H_MM: float = 280.0

    # River level buffers in meters relative to Warning and Danger levels
    RIVER_WARNING_BUFFER_METERS: float = 1.0
    RIVER_DANGER_BUFFER_METERS: float = 0.5

    # Dam release thresholds in cusecs (cubic feet per second)
    DAM_HIGH_DISCHARGE_CUSECS: float = 50000.0
    DAM_CRITICAL_DISCHARGE_CUSECS: float = 100000.0

    # Evidence freshness threshold in hours
    FRESHNESS_MAX_HOURS: int = 24
    RIVER_FRESHNESS_MAX_HOURS: int = 12
    WEATHER_FRESHNESS_MAX_HOURS: int = 24
    DAM_FRESHNESS_MAX_HOURS: int = 24
    CRITICAL_FRESHNESS_MAX_HOURS: int = 12

    # Notification Dispatch Safety (MOCK, SANDBOX, LIVE)
    NOTIFICATION_MODE: str = "MOCK"  # 'MOCK', 'SANDBOX', or 'LIVE'
    NOTIFICATION_SANDBOX_PHONE: Optional[str] = None
    NOTIFICATION_SANDBOX_EMAIL: Optional[str] = None
    SMS_GATEWAY_URL: Optional[str] = None
    SMS_GATEWAY_API_KEY: Optional[str] = None


settings = Settings()

