"""FastAPI common dependencies."""

from typing import Generator
from fastapi import Depends
from sqlalchemy.orm import Session
from backend.app.database.connection import get_db
from backend.app.core.security import verify_api_key

__all__ = ["get_db", "verify_api_key"]

