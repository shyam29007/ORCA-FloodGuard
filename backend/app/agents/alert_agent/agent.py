"""Agent 6: Alert Agent implementation."""

from typing import Any, Dict, List
import uuid
from backend.app.agents.base_agent import BaseAgent
from backend.app.schemas.agents import AgentName
from backend.app.schemas.alerts import AlertDraftSchema, AlertStatus, AlertChannel
from backend.app.schemas.flood import RiskLevel
from backend.app.core.llm_factory import get_llm
from backend.app.core.logging import logger


class AlertAgent(BaseAgent):
    """Specialist agent for advisory text drafting and multilingual citizen communication."""

    def __init__(self):
        super().__init__(AgentName.ALERT, provider_dependency="None (Deterministic Rule Engine)")

    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        village_name = state.get("village_name", "Village")
        village_id = state.get("village", {}).get("village_id", f"vil-{village_name.lower()}")
        overall_risk = state.get("overall_risk", RiskLevel.LOW)
        if isinstance(overall_risk, str):
            try:
                overall_risk = RiskLevel(overall_risk)
            except ValueError:
                overall_risk = RiskLevel.LOW

        assessment_id = state.get("assessment_id", f"fa-{uuid.uuid4().hex[:8]}")
        triggered_rules: List[str] = state.get("triggered_rules", [])
        evidence_summary: List[str] = state.get("evidence_summary", [])
        if not evidence_summary and triggered_rules:
            evidence_summary = [f"Rule triggered: {r}" for r in triggered_rules]

        rain_24h = state.get("rainfall_24h_mm", 0.0)
        river_warning = state.get("river_is_above_warning", False)
        river_danger = state.get("river_is_above_danger", False)
        max_dam = state.get("max_dam_discharge_cusecs", 0.0)

        punjabi_texts = {
            RiskLevel.CRITICAL: (
                f"ਸੰਕਟਕਾਲੀਨ ਹੜ੍ਹ ਚੇਤਾਵਨੀ - {village_name}: ਪਾਣੀ ਦਾ ਪੱਧਰ ਖ਼ਤਰੇ ਦੇ ਨਿਸ਼ਾਨ ਤੋਂ ਪਾਰ ਹੈ "
                f"ਅਤੇ ਡੈਮ ਤੋਂ {max_dam:,.0f} ਕਿਊਸਿਕ ਪਾਣੀ ਛੱਡਿਆ ਗਿਆ ਹੈ। ਤੁਰੰਤ ਨਜ਼ਦੀਕੀ ਉੱਚੇ ਸਥਾਨ ਜਾਂ ਰਾਹਤ ਕੈਂਪ ਵਿੱਚ ਪਹੁੰਚੋ। "
                f"ਸਹਾਇਤਾ ਲਈ 112 ਡਾਇਲ ਕਰੋ।"
            ),
            RiskLevel.HIGH: (
                f"ਉੱਚ ਹੜ੍ਹ ਚੇਤਾਵਨੀ - {village_name}: ਅਗਲੇ 24 ਘੰਟਿਆਂ ਵਿੱਚ ਭਾਰੀ ਮੀਂਹ ({rain_24h}mm) ਅਤੇ ਦਰਿਆ ਵਿੱਚ "
                f"ਪਾਣੀ ਵਧਣ ਦੀ ਸੰਭਾਵਨਾ ਹੈ। ਨੀਵੇਂ ਇਲਾਕਿਆਂ ਦੇ ਵਸਨੀਕ ਸੁਰੱਖਿਅਤ ਥਾਵਾਂ 'ਤੇ ਜਾਣ ਦੀ ਤਿਆਰੀ ਰੱਖਣ।"
            ),
            RiskLevel.MODERATE: (
                f"ਹੜ੍ਹ ਚੌਕਸੀ - {village_name}: ਮੌਸਮ ਵਿਭਾਗ ਵੱਲੋਂ ਮੀਂਹ ਦਾ ਅਨੁਮਾਨ ਹੈ। ਦਰਿਆ ਕੰਢੇ ਨਾ ਜਾਓ "
                f"ਅਤੇ ਪ੍ਰਸ਼ਾਸਨ ਦੀਆਂ ਹਦਾਇਤਾਂ ਸੁਣਦੇ ਰਹੋ।"
            ),
            RiskLevel.LOW: (
                f"ਸਧਾਰਨ ਸਥਿਤੀ - {village_name}: ਹੜ੍ਹ ਦਾ ਕੋਈ ਤੁਰੰਤ ਖ਼ਤਰਾ ਨਹੀਂ ਹੈ। ਸਥਿਤੀ 'ਤੇ ਨਜ਼ਰ ਰੱਖੀ ਜਾ ਰਹੀ ਹੈ।"
            ),
            RiskLevel.INSUFFICIENT_EVIDENCE: (
                f"ਸੂਚਨਾ - {village_name}: ਨਾਕਾਫ਼ੀ ਡਾਟਾ ਕਾਰਨ ਪੂਰਾ ਅਨੁਮਾਨ ਉਪਲਬਧ ਨਹੀਂ ਹੈ। ਸਥਾਨਕ ਪ੍ਰਸ਼ਾਸਨ ਨਾਲ ਸੰਪਰਕ ਬਣਾਈ ਰੱਖੋ।"
            ),
        }

        english_texts = {
            RiskLevel.CRITICAL: (
                f"CRITICAL FLOOD EMERGENCY ALERT for {village_name}: Upstream dam discharge of {max_dam:,.0f} cusecs "
                f"and active embankment cresting pose immediate danger. Evacuate low-lying sectors along designated corridors immediately."
            ),
            RiskLevel.HIGH: (
                f"HIGH FLOOD WARNING for {village_name}: Heavy 24h rainfall of {rain_24h}mm and river stage at warning levels. "
                f"Residents in vulnerable floodplains should prepare for precautionary evacuation to designated relief centres."
            ),
            RiskLevel.MODERATE: (
                f"FLOOD ADVISORY for {village_name}: Sustained monsoon precipitation anticipated. Avoid riverbanks and stay alert to civil administration bulletins."
            ),
            RiskLevel.LOW: (
                f"NORMAL CONDITIONS for {village_name}: No imminent inundation risk detected. Hydrological conditions remain within nominal limits."
            ),
            RiskLevel.INSUFFICIENT_EVIDENCE: (
                f"NOTICE for {village_name}: Comprehensive automated risk calculation unavailable due to unconfigured live telemetry feeds. Consult district administration."
            ),
        }

        llm = get_llm()
        punjabi_msg = punjabi_texts.get(overall_risk, punjabi_texts[RiskLevel.LOW])
        english_msg = english_texts.get(overall_risk, english_texts[RiskLevel.LOW])

        if llm.is_available() and overall_risk in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            try:
                prompt = (
                    f"Refine this official flood alert for village {village_name}, Punjab. "
                    f"Risk level: {overall_risk.value}. 24h rain: {rain_24h}mm, River warning breached: {river_warning}, Dam discharge: {max_dam:,.0f} cusecs. "
                    f"Provide clear, non-panicking, actionable safety advice in English (2 sentences)."
                )
                refined_en = llm.generate(prompt=prompt, system_prompt="You are an official Punjab State Disaster Management Authority advisor.")
                if refined_en and len(refined_en.strip()) > 20:
                    english_msg = refined_en.strip()
            except Exception as e:
                logger.warning("LLM refinement skipped: %s; using deterministic verified template.", str(e))

        headline = f"Flood Advisory for {village_name}: Risk Level {overall_risk.value}"
        action = (
            "Evacuate to designated relief shelters immediately via verified corridors."
            if overall_risk in (RiskLevel.HIGH, RiskLevel.CRITICAL)
            else "Monitor local news and stay away from river embankments."
        )

        draft = AlertDraftSchema(
            alert_id=f"alert-{uuid.uuid4().hex[:8]}",
            assessment_id=assessment_id,
            village_id=village_id,
            village_name=village_name,
            risk_level=overall_risk,
            headline=headline,
            english_text=english_msg,
            punjabi_text=punjabi_msg,
            recommended_action=action,
            target_channels=[AlertChannel.SMS, AlertChannel.VOICE_CALL],
            status=AlertStatus.PENDING_APPROVAL,
            evidence_summary=evidence_summary,
        )

        trace_meta = {
            "provider_dependency": "None (Deterministic Rule Engine)",
            "evidence_mode": "DERIVED",
            "data_freshness": "FRESH",
            "input_evidence_refs": ["state.overall_risk", "state.rainfall_24h_mm", "state.river_level_meters", "state.max_dam_discharge_cusecs"],
            "output_evidence_refs": [draft.alert_id],
            "is_schema_validated": True,
            "is_source_authenticated": False,
            "is_data_freshness_validated": False,
            "diagnostic_message": "Generated bilingual advisory draft with Punjabi & English templates; requires human emergency official authorization before broadcast.",
        }

        return {
            "alert_draft": draft.model_dump(),
            "alert_draft_id": draft.alert_id,
            "status": "SUCCESS",
            "notes": ["Alert draft prepared with English & Punjabi copy. Status is PENDING_APPROVAL."],
            "_trace_meta": trace_meta,
        }
