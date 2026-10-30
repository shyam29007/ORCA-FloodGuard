"""Unit tests verifying each of the six specialist agents independently."""

from backend.app.agents.location_agent import LocationAgent
from backend.app.agents.weather_agent import WeatherAgent
from backend.app.agents.river_agent import RiverAgent
from backend.app.agents.dam_agent import DamAgent
from backend.app.agents.gis_evacuation_agent import GISEvacuationAgent
from backend.app.agents.alert_agent import AlertAgent
from backend.app.schemas.flood import RiskLevel
from backend.app.schemas.agents import AgentExecutionStatus


def test_location_agent():
    agent = LocationAgent()
    state = {"village_name": "Gidderpindi", "latitude": 31.1465, "longitude": 75.1872}
    result = agent.run(state, run_id="test-run-loc")

    assert result["status"] == "SUCCESS"
    assert result["village_name"] == "Gidderpindi"
    assert result["district"] == "Jalandhar"
    assert result["river_basin"] == "Sutlej"
    assert "_trace" in result
    assert result["_trace"].status == AgentExecutionStatus.COMPLETED


def test_weather_agent():
    agent = WeatherAgent()
    state = {"latitude": 31.1465, "longitude": 75.1872, "district": "Jalandhar"}
    result = agent.run(state, run_id="test-run-weather")

    assert result["status"] == "SUCCESS"
    assert "weather_data" in result
    assert result["rainfall_24h_mm"] >= 0.0
    assert result["rainfall_48h_mm"] >= result["rainfall_24h_mm"]
    assert len(result["evidence_records"]) > 0


def test_river_agent():
    agent = RiverAgent()
    state = {"latitude": 31.1465, "longitude": 75.1872}
    result = agent.run(state, run_id="test-run-river")

    assert result["status"] == "SUCCESS"
    assert "river_data" in result
    assert result["river_data"]["station"]["station_id"] == "CWC_SUTLEJ_LOHIAN"
    assert len(result["evidence_records"]) > 0


def test_dam_agent():
    agent = DamAgent()
    state = {"river_basin": "Sutlej"}
    result = agent.run(state, run_id="test-run-dam")

    assert result["status"] == "SUCCESS"
    assert len(result["dam_data"]) > 0
    assert result["max_dam_discharge_cusecs"] >= 0.0
    assert len(result["evidence_records"]) > 0


def test_gis_evacuation_agent():
    agent = GISEvacuationAgent()
    state = {"village_name": "Gidderpindi", "latitude": 31.1465, "longitude": 75.1872, "district": "Jalandhar"}
    result = agent.run(state, run_id="test-run-gis")

    assert result["status"] == "SUCCESS"
    assert "gis_evacuation_data" in result
    assert len(result["gis_evacuation_data"]["relief_centres"]) > 0
    assert len(result["gis_evacuation_data"]["evacuation_routes"]) > 0
    # Strict check: No uninspected route is labeled VERIFIED_SAFE blindly
    for rt in result["gis_evacuation_data"]["evacuation_routes"]:
        assert rt["verification_status"] in ("CANDIDATE", "UNVERIFIED", "VERIFIED_OPEN", "REPORTED_BLOCKED", "UNAVAILABLE")


def test_alert_agent():
    agent = AlertAgent()
    state = {
        "village_name": "Gidderpindi",
        "overall_risk": RiskLevel.HIGH,
        "rainfall_24h_mm": 65.0,
        "river_is_above_warning": True,
        "max_dam_discharge_cusecs": 70000.0,
        "triggered_rules": ["RULE_02_HEAVY_RAIN_NEAR_RIVER", "RULE_04_DAM_HIGH_DISCHARGE"],
    }
    result = agent.run(state, run_id="test-run-alert")

    assert result["status"] == "SUCCESS"
    assert "alert_draft" in result
    alert = result["alert_draft"]
    assert alert["risk_level"] == "HIGH"
    assert "english_text" in alert and len(alert["english_text"]) > 10
    assert "punjabi_text" in alert and len(alert["punjabi_text"]) > 10
    assert alert["status"] == "PENDING_APPROVAL"  # Human approval strictly required

