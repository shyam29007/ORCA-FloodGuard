"""Operational audit logging service."""

from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.app.database.repositories import AuditLogRepository
from backend.app.database.models import AuditLog


class AuditService:
    def __init__(self, db: Session):
        self.repo = AuditLogRepository(db)

    def log(
        self,
        entity_type: str,
        entity_id: str,
        action: str,
        actor: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        return self.repo.log(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            actor=actor,
            details=details,
        )

