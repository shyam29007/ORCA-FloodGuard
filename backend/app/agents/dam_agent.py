"""Agent 4: Dam Agent.

Retrieves reservoir storage levels, inflow, and controlled spillway release telemetry
from BBMB / PSPCL dams affecting Punjab river channels.
"""

from typing import Any, Dict
from backend.app.agents.base_agent import BaseAgent
from backend.app.schemas.agents import AgentName
from backend.app.schemas.dam import DamAgentOutput
from backend.app.tools.dam_tool import fetch_dam_telemetry


class DamAgent(BaseAgent):
    """Specialist agent for upstream reservoir telemetry and spillway discharge."""

    def __init__(self):
        super().__init__(AgentName.DAM)

    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        basin = state.get("river_basin", "Sutlej")
        allow_simulated = state.get("include_simulated_fallback", True)

        dams, evidence_records = fetch_dam_telemetry(
            river_basin=basin,
            allow_simulated=allow_simulated,
        )

        max_discharge = max((d.outflow_discharge_cusecs or 0.0 for d in dams), default=0.0)

        output = DamAgentOutput(
            relevant_dams=dams,
            max_downstream_discharge_cusecs=max_discharge,
            evidence_records=evidence_records,
            status="SUCCESS",
            notes=[f"Tracked {len(dams)} dams in basin '{basin}'. Max downstream discharge: {max_discharge:,.0f} cusecs"],
        )

        return {
            "dam_data": [d.model_dump() for d in dams],
            "evidence_records": [ev.model_dump() for ev in evidence_records],
            "dam_output": output.model_dump(),
            "max_dam_discharge_cusecs": max_discharge,
            "status": "SUCCESS",
        }

