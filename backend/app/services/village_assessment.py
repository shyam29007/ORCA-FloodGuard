"""Village assessment service re-exports."""

from backend.app.services.risk_assessment import DeterministicRiskEngine

__all__ = ["DeterministicRiskEngine"]

