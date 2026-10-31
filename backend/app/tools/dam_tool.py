"""Dam telemetry and reservoir discharge tool for Bhakra, Pong, and Ranjit Sagar dams."""

from datetime import datetime, timezone
from typing import Optional, Tuple, List
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.schemas.dam import DamInformation
from backend.app.schemas.evidence import EvidenceRecordSchema, EvidenceStatus, EvidenceQuality
from backend.app.integrations.bbmb_provider import BBMBDamProvider

PUNJAB_DAMS = [
    DamInformation(
        dam_id="BBMB_BHAKRA_DAM",
        name="Bhakra Dam",
        river="Sutlej",
        full_reservoir_level_meters=512.06,  # 1680 ft
        current_water_level_meters=507.50,
        capacity_percent=88.5,
        inflow_cusecs=45000.0,
        outflow_discharge_cusecs=42000.0,
        spillway_gates_open=4,
        status=EvidenceStatus.LIVE,
        is_high_discharge=False,
        is_critical_discharge=False,
    ),
    DamInformation(
        dam_id="BBMB_PONG_DAM",
        name="Pong Dam",
        river="Beas",
        full_reservoir_level_meters=426.72,  # 1400 ft
        current_water_level_meters=423.10,
        capacity_percent=82.0,
        inflow_cusecs=38000.0,
        outflow_discharge_cusecs=35000.0,
        spillway_gates_open=2,
        status=EvidenceStatus.LIVE,
        is_high_discharge=False,
        is_critical_discharge=False,
    ),
    DamInformation(
        dam_id="PSPCL_RANJIT_SAGAR_DAM",
        name="Ranjit Sagar Dam (Thein Dam)",
        river="Ravi",
        full_reservoir_level_meters=527.91,
        current_water_level_meters=520.40,
        capacity_percent=76.4,
        inflow_cusecs=22000.0,
        outflow_discharge_cusecs=18000.0,
        spillway_gates_open=0,
        status=EvidenceStatus.LIVE,
        is_high_discharge=False,
        is_critical_discharge=False,
    ),
]


def fetch_dam_telemetry(
    river_basin: Optional[str] = "Sutlej",
    allow_simulated: bool = True,
) -> Tuple[List[DamInformation], List[EvidenceRecordSchema]]:
    """Retrieve dam reservoir levels and controlled spillway release telemetry."""
    now = datetime.now(timezone.utc)
    evidence_records: List[EvidenceRecordSchema] = []

    # 1. Attempt live API retrieval via BBMBDamProvider if configured
    provider = BBMBDamProvider()
    if provider.is_configured():
        try:
            return provider.fetch_dam_telemetry(river_basin=river_basin)
        except Exception as e:
            logger.warning("BBMB dam provider failed: %s; falling back according to simulation configuration.", str(e))

    # 2. Fallback: Simulation or Explicit UNAVAILABLE
    relevant_dams: List[DamInformation] = []
    status = EvidenceStatus.SIMULATED if allow_simulated else EvidenceStatus.UNAVAILABLE
    source_name = "BBMB_TELEMETRY_SAMPLE" if allow_simulated else "BBMB"

    for base_dam in PUNJAB_DAMS:
        # Filter relevant to river basin if specified
        if river_basin and river_basin.lower() not in base_dam.river.lower() and base_dam.river.lower() not in river_basin.lower():
            continue

        discharge = base_dam.outflow_discharge_cusecs if allow_simulated else None
        d = DamInformation(
            dam_id=base_dam.dam_id,
            name=base_dam.name,
            river=base_dam.river,
            full_reservoir_level_meters=base_dam.full_reservoir_level_meters,
            current_water_level_meters=base_dam.current_water_level_meters if allow_simulated else None,
            capacity_percent=base_dam.capacity_percent if allow_simulated else None,
            inflow_cusecs=base_dam.inflow_cusecs if allow_simulated else None,
            outflow_discharge_cusecs=discharge,
            spillway_gates_open=base_dam.spillway_gates_open if allow_simulated else None,
            status=status,
            is_simulated=(status == EvidenceStatus.SIMULATED),
            last_updated=now,
            is_high_discharge=(discharge is not None and discharge >= settings.DAM_HIGH_DISCHARGE_CUSECS),
            is_critical_discharge=(discharge is not None and discharge >= settings.DAM_CRITICAL_DISCHARGE_CUSECS),
        )
        relevant_dams.append(d)

        ev = EvidenceRecordSchema(
            source=source_name,
            source_type="DAM_TELEMETRY",
            location={"dam_name": base_dam.name, "river": base_dam.river, "dam_id": base_dam.dam_id},
            parameter="dam_spillway_outflow",
            value=discharge,
            unit="cusecs",
            observed_at=now,
            retrieved_at=now,
            status=status,
            quality=EvidenceQuality.MEDIUM if allow_simulated else EvidenceQuality.LOW,
            dataset_name="BBMB / PSPCL Dam Bulletin",
            limitations="Simulated dam discharge based on standard monsoon release scenario." if allow_simulated else "Live dam telemetry feed is unconfigured or unavailable.",
            eligibility_reason="SIMULATION_DEMO" if allow_simulated else "MEASUREMENT_UNAVAILABLE",
        )
        evidence_records.append(ev)

    return relevant_dams, evidence_records
