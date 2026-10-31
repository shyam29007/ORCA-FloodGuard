"""Agent 4: Dam Agent implementation."""

from typing import Any, Dict
from backend.app.agents.base_agent import BaseAgent
from backend.app.schemas.agents import AgentName
from backend.app.schemas.dam import DamAgentOutput
from backend.app.tools.dam_tool import fetch_dam_telemetry


class DamAgent(BaseAgent):
    """Specialist agent for upstream reservoir telemetry and spillway discharge."""

    def __init__(self):
        super().__init__(AgentName.DAM, provider_dependency="BBMB (Bhakra Beas Management Board)")

    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        basin = state.get("river_basin", "Sutlej")
        allow_simulated = state.get("include_simulated_fallback", True)

        dams, evidence_records = fetch_dam_telemetry(
            river_basin=basin,
            allow_simulated=allow_simulated,
        )

        has_discharge = any(d.outflow_discharge_cusecs is not None for d in dams)
        any_sim = any(getattr(d, "is_simulated", False) for d in dams)
        is_live = (not any_sim) and has_discharge
        is_sim = any_sim and has_discharge

        max_discharge = max((d.outflow_discharge_cusecs or 0.0 for d in dams), default=0.0)

        if is_live:
            ev_mode = "LIVE"
            freshness = "FRESH"
            diag = f"Live BBMB telemetry ingested for {len(dams)} dams in {basin} basin (Max discharge: {max_discharge:,.0f} cusecs)."
        elif is_sim:
            ev_mode = "SIMULATED"
            freshness = "SIMULATED_SCENARIO"
            diag = f"BBMB telemetry unconfigured; operating with simulated scenario reservoir release model for {len(dams)} dams ({basin} basin)."
        else:
            ev_mode = "UNAVAILABLE"
            freshness = "NOT_AVAILABLE"
            diag = f"BBMB telemetry unconfigured and simulation disabled for {basin} basin reservoirs (Operational Mode)."

        output = DamAgentOutput(
            relevant_dams=dams,
            max_downstream_discharge_cusecs=max_discharge,
            evidence_records=evidence_records,
            status="SUCCESS",
            notes=[f"Tracked {len(dams)} dams in basin '{basin}'. Max downstream discharge: {max_discharge:,.0f} cusecs"],
        )

        trace_meta = {
            "provider_dependency": "BBMB (Bhakra Beas Management Board)",
            "evidence_mode": ev_mode,
            "data_freshness": freshness,
            "input_evidence_refs": ["state.river_basin"],
            "output_evidence_refs": [getattr(ev, "evidence_id", f"ev-d-{i}") for i, ev in enumerate(evidence_records)],
            "is_schema_validated": True,
            "is_source_authenticated": is_live,
            "is_data_freshness_validated": is_live,
            "diagnostic_message": diag,
        }

        return {
            "dam_data": [d.model_dump() for d in dams],
            "evidence_records": [ev.model_dump() for ev in evidence_records],
            "dam_output": output.model_dump(),
            "max_dam_discharge_cusecs": max_discharge,
            "status": "SUCCESS",
            "_trace_meta": trace_meta,
        }
