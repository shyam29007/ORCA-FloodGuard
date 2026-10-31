"""Custom exception classes for ORCA-FloodGuard domain errors."""

from typing import Any, Dict, Optional


class FloodGuardException(Exception):
    """Base exception for all ORCA-FloodGuard domain errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ProviderException(FloodGuardException):
    """Raised when an external data provider fails, times out, or returns invalid data."""
    pass


class ProviderTimeoutException(ProviderException):
    """Raised when an external provider request times out."""
    pass


class EvidenceValidationException(FloodGuardException):
    """Raised when evidence fails validation checks."""
    pass


class InsufficientEvidenceException(FloodGuardException):
    """Raised when critical evidence is missing, stale, or spatially irrelevant."""
    pass


class VillageNotFoundException(FloodGuardException):
    """Raised when a requested village is not found in database or geocoding."""
    pass


class AlertNotFoundException(FloodGuardException):
    """Raised when an alert draft is not found."""
    pass


class AlertAlreadyApprovedException(FloodGuardException):
    """Raised when an alert draft has already been approved or rejected."""
    pass


class LLMProviderException(FloodGuardException):
    """Raised when LLM service is misconfigured or fails."""
    pass

