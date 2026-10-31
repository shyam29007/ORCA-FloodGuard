"""Agent execution tracking and audit trace endpoints."""

from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.api.dependencies import get_db
from backend.app.schemas.common import ApiResponse
from backend.app.database.repositories import AgentExecutionRepository

router = APIRouter(prefix="/agents", tags=["Agent Execution"])


@router.get("/status/{run_id}", response_model=ApiResponse[Dict[str, Any]])
def get_run_status(
    run_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve high-level execution status of an orchestrator run."""
    repo = AgentExecutionRepository(db)
    executions = repo.get_by_run_id(run_id)
    if not executions:
        return ApiResponse(
            success=True,
            message="No persisted executions for this run_id (may be in-memory or pending)",
            data={"run_id": run_id, "status": "UNKNOWN", "agent_count": 0},
        )

    all_completed = all(e.status == "COMPLETED" for e in executions)
    has_failed = any(e.status == "FAILED" for e in executions)

    return ApiResponse(
        success=True,
        data={
            "run_id": run_id,
            "status": "FAILED" if has_failed else ("COMPLETED" if all_completed else "RUNNING"),
            "agent_count": len(executions),
            "agents_executed": [e.agent_name for e in executions],
        },
    )


@router.get("/trace/{run_id}", response_model=ApiResponse[List[Dict[str, Any]]])
def get_run_trace(
    run_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve full specialist agent execution trace log for an assessment run."""
    repo = AgentExecutionRepository(db)
    executions = repo.get_by_run_id(run_id)
    if not executions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No execution traces found for run_id '{run_id}'.",
        )

    traces = [
        {
            "execution_id": e.id,
            "agent_name": e.agent_name,
            "status": e.status,
            "started_at": e.started_at.isoformat() if e.started_at else None,
            "completed_at": e.completed_at.isoformat() if e.completed_at else None,
            "duration_ms": e.duration_ms,
            "inputs": e.inputs_json,
            "outputs": e.outputs_json,
            "provider_dependency": (e.outputs_json or {}).get("provider_dependency"),
            "evidence_mode": (e.outputs_json or {}).get("evidence_mode"),
            "data_freshness": (e.outputs_json or {}).get("data_freshness"),
            "input_evidence_refs": (e.outputs_json or {}).get("input_evidence_refs", []),
            "output_evidence_refs": (e.outputs_json or {}).get("output_evidence_refs", []),
            "is_execution_completed": (e.outputs_json or {}).get("is_execution_completed", True),
            "is_schema_validated": (e.outputs_json or {}).get("is_schema_validated", True),
            "is_source_authenticated": (e.outputs_json or {}).get("is_source_authenticated", False),
            "is_data_freshness_validated": (e.outputs_json or {}).get("is_data_freshness_validated", False),
            "diagnostic_message": (e.outputs_json or {}).get("diagnostic_message"),
            "error_message": e.error_message,
        }
        for e in executions
    ]

    return ApiResponse(success=True, data=traces)
