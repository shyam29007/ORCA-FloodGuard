"""Deterministic Flood Risk Engine for Punjab villages.

Evaluates multi-factor hydrological evidence using explicit, auditable, and configurable rules.
Produces independent 24h, 48h, and 72h outlooks with separated confidence calibration reporting.
CRITICAL: LLM cannot calculate or override deterministic risk levels.
"""

from typing import Dict, Any, List, Optional, Tuple
from backend.app.core.config import settings
from backend.app.schemas.flood import RiskLevel, RiskOutlook
from backend.app.schemas.evidence import EvidenceRecordSchema, EvidenceCollectionSummary, EvidenceStatus
from backend.app.core.llm_factory import get_llm
from backend.app.core.logging import logger


class DeterministicRiskEngine:
    """Deterministic rule-based risk evaluation service."""

    @classmethod
    def assess_village_risk(
        cls,
        village_name: str,
        distance_to_river_km: float,
        is_low_lying: bool,
        rainfall_24h_mm: Optional[float],
        rainfall_48h_mm: Optional[float],
        rainfall_72h_mm: Optional[float],
        river_above_warning: bool,
        river_above_danger: bool,
        river_buffer_to_danger: Optional[float],
        max_dam_discharge_cusecs: float,
        validation_summary: EvidenceCollectionSummary,
        contributing_evidence: List[EvidenceRecordSchema],
        operational_mode: bool = False,
    ) -> Tuple[RiskLevel, Dict[str, RiskOutlook], List[str], str, str, str, List[str]]:
        """Perform deterministic evaluation across 24h, 48h, and 72h windows.

        Returns (overall_risk, outlooks, triggered_rules, explanation, assessment_mode, assessment_status, limitations).
        """
        evidence_by_param: Dict[str, List[EvidenceRecordSchema]] = {}
        for ev in contributing_evidence:
            evidence_by_param.setdefault(ev.parameter, []).append(ev)

        has_simulated_critical = any(
            ev.status == EvidenceStatus.SIMULATED and ev.parameter in ("rainfall_24h", "river_water_level")
            for ev in contributing_evidence
        )

        assessment_mode = "OPERATIONAL" if (operational_mode and not has_simulated_critical) else "SIMULATION_DEMO"
        limitations: List[str] = [
            "Deterministic hydrological thresholds are configurable operational baselines and not statistical flood probability forecasts.",
            "Confidence scores are explicitly uncalibrated (NOT_CALIBRATED) in absence of regional empirical hydrological calibration.",
        ]

        if has_simulated_critical:
            limitations.append(
                "Demonstration scenario: Critical rainfall or river gauge telemetry is SIMULATED and cannot be used for operational public dispatch."
            )

        # Gate 1: Check if validation flagged insufficient evidence
        if not validation_summary.is_valid_for_assessment:
            triggered_rules = ["RULE_00_CRITICAL_EVIDENCE_MISSING"]
            outlooks: Dict[str, RiskOutlook] = {}
            for h in ["24h", "48h", "72h"]:
                h_rain = rainfall_24h_mm if h == "24h" else (rainfall_48h_mm if h == "48h" else rainfall_72h_mm)
                outlooks[h] = RiskOutlook(
                    horizon=h,
                    risk_level=RiskLevel.INSUFFICIENT_EVIDENCE,
                    confidence_status="NOT_CALIBRATED",
                    confidence_score=None,
                    confidence=None,
                    primary_factors=[f"Missing critical telemetry: {', '.join(validation_summary.critical_missing)}"],
                    triggered_rules=triggered_rules,
                    supporting_evidence_ids=[],
                    rainfall_forecast_mm=h_rain,
                )
            explanation = (
                f"Assessment for {village_name} withheld as INSUFFICIENT_EVIDENCE: "
                f"{'; '.join(validation_summary.validation_messages)}"
            )
            assessment_status = "INSUFFICIENT_EVIDENCE"
            return RiskLevel.INSUFFICIENT_EVIDENCE, outlooks, triggered_rules, explanation, assessment_mode, assessment_status, limitations

        # Gate 2: Operational mode strictly requires verified LIVE critical rainfall and river stage
        has_live_rainfall = any(
            ev.status == EvidenceStatus.LIVE and ev.parameter == "rainfall_24h"
            for ev in contributing_evidence
        )
        has_live_river = any(
            ev.status == EvidenceStatus.LIVE and ev.parameter == "river_water_level"
            for ev in contributing_evidence
        )
        if operational_mode and (not has_live_rainfall or not has_live_river):
            missing_crit: List[str] = []
            if not has_live_rainfall:
                missing_crit.append("live rainfall_24h")
            if not has_live_river:
                missing_crit.append("live river_water_level")
            triggered_rules = ["RULE_00_CRITICAL_EVIDENCE_MISSING"]
            outlooks: Dict[str, RiskOutlook] = {}
            for h in ["24h", "48h", "72h"]:
                h_rain = rainfall_24h_mm if h == "24h" else (rainfall_48h_mm if h == "48h" else rainfall_72h_mm)
                outlooks[h] = RiskOutlook(
                    horizon=h,
                    risk_level=RiskLevel.INSUFFICIENT_EVIDENCE,
                    confidence_status="NOT_CALIBRATED",
                    confidence_score=None,
                    confidence=None,
                    primary_factors=[f"Operational assessment requires verified live data. Missing: {', '.join(missing_crit)}"],
                    triggered_rules=triggered_rules,
                    supporting_evidence_ids=[],
                    rainfall_forecast_mm=h_rain,
                )
            explanation = (
                f"Assessment for {village_name} withheld as INSUFFICIENT_EVIDENCE: "
                f"Critical live observations missing ({', '.join(missing_crit)}). "
                "Operational safety policy strictly forbids issuing flood warning outlooks without verified live sensors."
            )
            assessment_status = "INSUFFICIENT_EVIDENCE"
            return RiskLevel.INSUFFICIENT_EVIDENCE, outlooks, triggered_rules, explanation, "OPERATIONAL", assessment_status, limitations

        # Map supporting evidence IDs for each horizon
        ev_ids_24 = [ev.evidence_id for ev in evidence_by_param.get("rainfall_24h", []) + evidence_by_param.get("river_water_level", [])]
        ev_ids_48 = [ev.evidence_id for ev in evidence_by_param.get("rainfall_48h", []) + evidence_by_param.get("river_water_level", [])]
        ev_ids_72 = [ev.evidence_id for ev in evidence_by_param.get("rainfall_72h", []) + evidence_by_param.get("river_water_level", [])]

        triggered_rules_global: List[str] = []

        # 24-Hour Outlook
        outlook_24h, rules_24 = cls._evaluate_window(
            horizon="24h",
            rainfall_mm=rainfall_24h_mm,
            rain_mod_thresh=settings.RAIN_MODERATE_24H_MM,
            rain_high_thresh=settings.RAIN_HIGH_24H_MM,
            rain_crit_thresh=settings.RAIN_CRITICAL_24H_MM,
            distance_to_river_km=distance_to_river_km,
            is_low_lying=is_low_lying,
            river_above_warning=river_above_warning,
            river_above_danger=river_above_danger,
            river_buffer_to_danger=river_buffer_to_danger,
            max_dam_discharge_cusecs=max_dam_discharge_cusecs,
            supporting_ids=ev_ids_24,
        )
        triggered_rules_global.extend(rules_24)

        # 48-Hour Outlook
        outlook_48h, rules_48 = cls._evaluate_window(
            horizon="48h",
            rainfall_mm=rainfall_48h_mm,
            rain_mod_thresh=settings.RAIN_MODERATE_48H_MM,
            rain_high_thresh=settings.RAIN_HIGH_48H_MM,
            rain_crit_thresh=settings.RAIN_CRITICAL_48H_MM,
            distance_to_river_km=distance_to_river_km,
            is_low_lying=is_low_lying,
            river_above_warning=river_above_warning,
            river_above_danger=river_above_danger,
            river_buffer_to_danger=river_buffer_to_danger,
            max_dam_discharge_cusecs=max_dam_discharge_cusecs,
            supporting_ids=ev_ids_48,
        )
        triggered_rules_global.extend(rules_48)

        # 72-Hour Outlook
        outlook_72h, rules_72 = cls._evaluate_window(
            horizon="72h",
            rainfall_mm=rainfall_72h_mm,
            rain_mod_thresh=settings.RAIN_MODERATE_72H_MM,
            rain_high_thresh=settings.RAIN_HIGH_72H_MM,
            rain_crit_thresh=settings.RAIN_CRITICAL_72H_MM,
            distance_to_river_km=distance_to_river_km,
            is_low_lying=is_low_lying,
            river_above_warning=river_above_warning,
            river_above_danger=river_above_danger,
            river_buffer_to_danger=river_buffer_to_danger,
            max_dam_discharge_cusecs=max_dam_discharge_cusecs,
            supporting_ids=ev_ids_72,
        )
        triggered_rules_global.extend(rules_72)

        outlooks = {
            "24h": outlook_24h,
            "48h": outlook_48h,
            "72h": outlook_72h,
        }

        # Overall risk corresponds to maximum risk across the forecast horizons
        hierarchy = [
            RiskLevel.LOW,
            RiskLevel.MODERATE,
            RiskLevel.HIGH,
            RiskLevel.CRITICAL,
        ]
        max_idx = max(hierarchy.index(o.risk_level) for o in outlooks.values() if o.risk_level in hierarchy)
        overall_risk = hierarchy[max_idx]

        unique_triggered = list(dict.fromkeys(triggered_rules_global))
        assessment_status = "SIMULATED_DEMO" if has_simulated_critical else "OPERATIONAL"

        # Generate deterministic explanation
        explanation = cls._generate_explanation(
            village_name=village_name,
            overall_risk=overall_risk,
            outlooks=outlooks,
            triggered_rules=unique_triggered,
            distance_to_river_km=distance_to_river_km,
            max_dam_discharge_cusecs=max_dam_discharge_cusecs,
            is_simulated=has_simulated_critical,
        )

        return overall_risk, outlooks, unique_triggered, explanation, assessment_mode, assessment_status, limitations

    @classmethod
    def _evaluate_window(
        cls,
        horizon: str,
        rainfall_mm: Optional[float],
        rain_mod_thresh: float,
        rain_high_thresh: float,
        rain_crit_thresh: float,
        distance_to_river_km: float,
        is_low_lying: bool,
        river_above_warning: bool,
        river_above_danger: bool,
        river_buffer_to_danger: Optional[float],
        max_dam_discharge_cusecs: float,
        supporting_ids: List[str],
    ) -> Tuple[RiskOutlook, List[str]]:
        """Evaluate deterministic risk for an individual time horizon without arbitrary confidence scores."""
        rules: List[str] = []
        factors: List[str] = []

        # Check CRITICAL conditions
        is_critical = False
        if river_above_danger:
            is_critical = True
            rules.append("RULE_CRIT_01_RIVER_ABOVE_DANGER")
            factors.append("River water stage exceeds designated Danger Level.")
        if max_dam_discharge_cusecs >= settings.DAM_CRITICAL_DISCHARGE_CUSECS:
            is_critical = True
            rules.append("RULE_CRIT_02_DAM_CRITICAL_DISCHARGE")
            factors.append(f"Upstream dam discharge ({max_dam_discharge_cusecs:,.0f} cusecs) exceeds emergency threshold.")
        if rainfall_mm is not None and rainfall_mm >= rain_crit_thresh and is_low_lying:
            is_critical = True
            rules.append("RULE_CRIT_03_EXTREME_RAINFALL_LOW_LYING")
            factors.append(f"Extreme rainfall ({rainfall_mm:.1f}mm) over low-lying floodplain.")

        if is_critical:
            return (
                RiskOutlook(
                    horizon=horizon,
                    risk_level=RiskLevel.CRITICAL,
                    confidence_status="NOT_CALIBRATED",
                    confidence_score=None,
                    confidence=None,
                    primary_factors=factors,
                    triggered_rules=rules,
                    supporting_evidence_ids=supporting_ids,
                    rainfall_forecast_mm=rainfall_mm,
                    river_proximity_risk="CRITICAL",
                    dam_discharge_risk="CRITICAL" if max_dam_discharge_cusecs >= settings.DAM_HIGH_DISCHARGE_CUSECS else "NORMAL",
                ),
                rules,
            )

        # Check HIGH conditions
        is_high = False
        if river_above_warning:
            is_high = True
            rules.append("RULE_HIGH_01_RIVER_ABOVE_WARNING")
            factors.append("River water stage has crossed the Warning Level threshold.")
        if rainfall_mm is not None and rainfall_mm >= rain_high_thresh and distance_to_river_km <= 5.0:
            is_high = True
            rules.append("RULE_HIGH_02_HEAVY_RAIN_NEAR_RIVER")
            factors.append(f"Heavy rainfall ({rainfall_mm:.1f}mm) within {distance_to_river_km}km of active river course.")
        if max_dam_discharge_cusecs >= settings.DAM_HIGH_DISCHARGE_CUSECS:
            is_high = True
            rules.append("RULE_HIGH_03_DAM_HIGH_DISCHARGE")
            factors.append(f"High upstream dam discharge ({max_dam_discharge_cusecs:,.0f} cusecs) surging downstream.")
        if river_buffer_to_danger is not None and 0.0 < river_buffer_to_danger <= settings.RIVER_DANGER_BUFFER_METERS:
            is_high = True
            rules.append("RULE_HIGH_04_RIVER_APPROACHING_DANGER")
            factors.append(f"River gauge within {river_buffer_to_danger:.2f}m of critical danger mark.")

        if is_high:
            return (
                RiskOutlook(
                    horizon=horizon,
                    risk_level=RiskLevel.HIGH,
                    confidence_status="NOT_CALIBRATED",
                    confidence_score=None,
                    confidence=None,
                    primary_factors=factors,
                    triggered_rules=rules,
                    supporting_evidence_ids=supporting_ids,
                    rainfall_forecast_mm=rainfall_mm,
                    river_proximity_risk="HIGH",
                    dam_discharge_risk="HIGH" if max_dam_discharge_cusecs >= settings.DAM_HIGH_DISCHARGE_CUSECS else "NORMAL",
                ),
                rules,
            )

        # Check MODERATE conditions
        is_moderate = False
        if rainfall_mm is not None and rainfall_mm >= rain_mod_thresh:
            is_moderate = True
            rules.append("RULE_MOD_01_MODERATE_RAINFALL")
            factors.append(f"Precipitation forecast ({rainfall_mm:.1f}mm) exceeds moderate catchment threshold.")
        if river_buffer_to_danger is not None and settings.RIVER_DANGER_BUFFER_METERS < river_buffer_to_danger <= settings.RIVER_WARNING_BUFFER_METERS:
            is_moderate = True
            rules.append("RULE_MOD_02_RIVER_APPROACHING_WARNING")
            factors.append("River stage approaching designated warning mark.")

        if is_moderate:
            return (
                RiskOutlook(
                    horizon=horizon,
                    risk_level=RiskLevel.MODERATE,
                    confidence_status="NOT_CALIBRATED",
                    confidence_score=None,
                    confidence=None,
                    primary_factors=factors,
                    triggered_rules=rules,
                    supporting_evidence_ids=supporting_ids,
                    rainfall_forecast_mm=rainfall_mm,
                    river_proximity_risk="MODERATE",
                    dam_discharge_risk="NORMAL",
                ),
                rules,
            )

        # Default to LOW
        rules.append("RULE_LOW_01_NORMAL_HYDROMETEOROLOGICAL_BASELINE")
        if rainfall_mm is not None:
            factors.append("Forecast rainfall and gauge telemetry are within safe, normal operating parameters.")
        else:
            factors.append("Rainfall forecast telemetry is unavailable; gauge and dam telemetry are within safe baseline.")
        return (
            RiskOutlook(
                horizon=horizon,
                risk_level=RiskLevel.LOW,
                confidence_status="NOT_CALIBRATED",
                confidence_score=None,
                confidence=None,
                primary_factors=factors,
                triggered_rules=rules,
                supporting_evidence_ids=supporting_ids,
                rainfall_forecast_mm=rainfall_mm,
                river_proximity_risk="NORMAL",
                dam_discharge_risk="NORMAL",
            ),
            rules,
        )

    @classmethod
    def _generate_explanation(
        cls,
        village_name: str,
        overall_risk: RiskLevel,
        outlooks: Dict[str, RiskOutlook],
        triggered_rules: List[str],
        distance_to_river_km: float,
        max_dam_discharge_cusecs: float,
        is_simulated: bool = False,
    ) -> str:
        """Produce clear, evidence-grounded explanation without hallucinated confidence numbers."""
        def _fmt_rain(val: Optional[float]) -> str:
            return f"{val}mm rain" if val is not None else "rainfall data unavailable"

        demo_prefix = "[SIMULATION DEMO] " if is_simulated else ""
        base_summary = (
            f"{demo_prefix}Village {village_name} is assessed at {overall_risk.value} flood risk over the 72h window. "
            f"Distance to river corridor: {distance_to_river_km} km. Max upstream dam discharge: {max_dam_discharge_cusecs:,.0f} cusecs. "
            f"24h Outlook: {outlooks['24h'].risk_level.value} ({_fmt_rain(outlooks['24h'].rainfall_forecast_mm)}); "
            f"48h Outlook: {outlooks['48h'].risk_level.value} ({_fmt_rain(outlooks['48h'].rainfall_forecast_mm)}); "
            f"72h Outlook: {outlooks['72h'].risk_level.value} ({_fmt_rain(outlooks['72h'].rainfall_forecast_mm)}). "
            f"Triggered deterministic rules: {', '.join(triggered_rules)}. "
            f"Risk levels are deterministic and non-probabilistic."
        )

        llm = get_llm()
        if llm.is_available() and overall_risk in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            try:
                prompt = (
                    f"Synthesize an authoritative 2-sentence disaster management briefing from this deterministic data:\n"
                    f"{base_summary}\n"
                    f"Explain the primary hydrological drivers clearly. DO NOT invent or mention any percentage confidence scores."
                )
                refined = llm.generate(prompt=prompt, system_prompt="You are a senior hydrological advisor. Do not invent confidence scores.")
                if refined and len(refined.strip()) > 30 and "%" not in refined:
                    return f"{demo_prefix}{refined.strip()}"
            except Exception as e:
                logger.warning("LLM explanation synthesis fallback: %s", str(e))

        return base_summary
