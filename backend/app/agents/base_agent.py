"""Base specialist agent class with tracing, error handling, and performance timing."""

import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from backend.app.schemas.agents import (
    AgentName,
    AgentExecutionStatus,
    AgentExecutionTrace,
)
from backend.app.core.logging import logger


class BaseAgent(ABC):
    """Abstract base class for all specialist agents."""

    def __init__(self, name: AgentName):
        self.name = name

    @abstractmethod
    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute core agent logic. Must be implemented by subclasses."""
        raise NotImplementedError

    def run(self, state: Dict[str, Any], run_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute agent with comprehensive timing, error trapping, and trace capture."""
        actual_run_id = run_id or state.get("run_id", "local-run")
        start_time = time.perf_counter()
        started_at = datetime.now(timezone.utc)

        trace = AgentExecutionTrace(
            run_id=actual_run_id,
            agent_name=self.name,
            status=AgentExecutionStatus.RUNNING,
            started_at=started_at,
            inputs={k: str(v)[:200] for k, v in state.items() if k not in ("agent_traces", "evidence_pool")},
        )

        logger.info("[%s] Executing agent for run %s...", self.name.value, actual_run_id)

        try:
            output = self.execute(state)
            duration_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

            trace.status = AgentExecutionStatus.COMPLETED
            trace.completed_at = datetime.now(timezone.utc)
            trace.duration_ms = duration_ms
            trace.outputs = {k: str(v)[:200] for k, v in output.items() if k not in ("evidence_pool",)}

            logger.info("[%s] Completed successfully in %0.2fms", self.name.value, duration_ms)
            output["_trace"] = trace
            return output

        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            error_msg = f"Agent failed: {str(exc)}"
            logger.error("[%s] Execution error in %0.2fms: %s", self.name.value, duration_ms, error_msg, exc_info=True)

            trace.status = AgentExecutionStatus.FAILED
            trace.completed_at = datetime.now(timezone.utc)
            trace.duration_ms = duration_ms
            trace.error_message = error_msg

            # Do not crash the orchestrator; return error state safely
            return {
                "error": error_msg,
                "status": "FAILED",
                "_trace": trace,
            }

