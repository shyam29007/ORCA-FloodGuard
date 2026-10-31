"""API route integration tests covering all required endpoints."""

from backend.app.schemas.flood import RiskLevel


def test_flood_assess_and_query_endpoints(client):
    # 1. Assess
    req_body = {
        "village_name": "Gidderpindi",
        "district": "Jalandhar",
        "forecast_horizon_hours": 72,
        "include_simulated_fallback": True,
    }
    res = client.post("/api/flood/assess", json=req_body)
    assert res.status_code == 200
    data = res.json()["data"]
    assessment_id = data["assessment_id"]
    run_id = data["run_id"]
    village_id = data["village"]["village_id"]
    assert assessment_id is not None
    assert data["village"]["name"] == "Gidderpindi"
    assert data["overall_risk"] in ("LOW", "MODERATE", "HIGH", "CRITICAL", "INSUFFICIENT_EVIDENCE")

    # 2. Query assessment by ID
    get_res = client.get(f"/api/flood/assessments/{assessment_id}")
    assert get_res.status_code == 200
    assert get_res.json()["data"]["assessment_id"] == assessment_id

    # 3. Query village outlook
    outlook_res = client.get(f"/api/flood/villages/{village_id}/outlook")
    assert outlook_res.status_code == 200
    assert outlook_res.json()["data"]["village_id"] == village_id

    # 4. Check agent status and trace
    status_res = client.get(f"/api/agents/status/{run_id}")
    assert status_res.status_code == 200
    assert status_res.json()["data"]["run_id"] == run_id

    trace_res = client.get(f"/api/agents/trace/{run_id}")
    assert trace_res.status_code == 200
    traces = trace_res.json()["data"]
    assert len(traces) > 0


def test_weather_endpoints(client):
    res = client.get("/api/weather/forecast?latitude=31.1465&longitude=75.1872&district=Jalandhar")
    assert res.status_code == 200
    data = res.json()["data"]
    assert "rainfall_24h_mm" in data
    assert data["rainfall_24h_mm"] >= 0.0


def test_river_endpoints(client):
    # List stations
    stations_res = client.get("/api/river/stations")
    assert stations_res.status_code == 200
    stations = stations_res.json()["data"]
    assert len(stations) > 0
    st_id = stations[0]["station_id"]

    # Station reading
    reading_res = client.get(f"/api/river/readings/{st_id}")
    assert reading_res.status_code == 200
    assert reading_res.json()["data"]["station_id"] == st_id

    # Station status
    status_res = client.get(f"/api/river/status/{st_id}")
    assert status_res.status_code == 200
    assert "warning_level_m" in status_res.json()["data"]


def test_dam_endpoints(client):
    res = client.get("/api/dam/information?river_basin=Sutlej")
    assert res.status_code == 200
    dams = res.json()["data"]
    assert len(dams) > 0
    assert any("Bhakra" in d["name"] for d in dams)


def test_gis_and_evacuation_endpoints(client):
    # GIS location
    gis_res = client.get("/api/gis/location?latitude=31.1465&longitude=75.1872")
    assert gis_res.status_code == 200
    gis_data = gis_res.json()["data"]
    assert "elevation_meters" in gis_data
    assert "is_depression_zone" in gis_data

    # Relief centres
    rc_res = client.get("/api/evacuation/relief-centres")
    assert rc_res.status_code == 200
    rc_list = rc_res.json()["data"]
    assert len(rc_list) > 0

    # Evacuation routes
    routes_res = client.get("/api/evacuation/routes?latitude=31.1465&longitude=75.1872&village_name=Gidderpindi")
    assert routes_res.status_code == 200
    routes = routes_res.json()["data"]
    assert len(routes) > 0


def test_historical_replay_endpoints(client):
    # Start
    start_res = client.post(
        "/api/replay/start",
        json={"event_name": "2023_punjab_monsoon_floods", "target_villages": ["Gidderpindi"]},
    )
    assert start_res.status_code == 200
    rep_data = start_res.json()["data"]
    replay_id = rep_data["replay_id"]
    assert rep_data["current_step"] == 1

    # Get status
    status_res = client.get(f"/api/replay/{replay_id}")
    assert status_res.status_code == 200

    # Step
    step_res = client.post(f"/api/replay/{replay_id}/step", json={"steps_to_advance": 1})
    assert step_res.status_code == 200
    assert step_res.json()["data"]["current_step"] == 2


def test_resident_report_workflow(client):
    # 1. Upload report
    payload = {
        "village_name": "Shahkot",
        "latitude": 31.0827,
        "longitude": 75.3377,
        "water_level_inches": 18.5,
        "observations": "Water spilling from tributary near primary school.",
        "reporter_name": "Harpreet Singh",
    }
    up_res = client.post("/api/reports/upload", json=payload)
    assert up_res.status_code == 201
    report = up_res.json()["data"]
    report_id = report["report_id"]
    assert report["status"] == "PENDING"

    # 2. Get report
    get_res = client.get(f"/api/reports/{report_id}")
    assert get_res.status_code == 200

    # 3. Review report
    rev_payload = {
        "status": "VERIFIED",
        "reviewer_name": "Tehsildar Shahkot",
        "review_notes": "Field patwari verified localized inundation.",
        "confidence_weight": 0.95,
    }
    rev_res = client.post(f"/api/reports/{report_id}/review", json=rev_payload)
    assert rev_res.status_code == 200
    assert rev_res.json()["data"]["status"] == "VERIFIED"


def test_alert_drafting_and_approval_workflow(client):
    # 0. Create prerequisite assessment
    assess_res = client.post("/api/flood/assess", json={
        "village_name": "Phillaur",
        "forecast_horizon_hours": 24,
        "include_simulated_fallback": True,
        "operational_mode": False,
    })
    assert assess_res.status_code == 200
    assessment_id = assess_res.json()["data"]["assessment_id"]

    # 1. Draft alert linked to valid assessment
    draft_res = client.post(f"/api/alerts/draft?assessment_id={assessment_id}&village_name=Phillaur&overall_risk=HIGH&rainfall_24h_mm=78.0")
    assert draft_res.status_code == 201
    draft = draft_res.json()["data"]
    alert_id = draft["alert_id"]
    assert draft["status"] == "PENDING_APPROVAL"
    assert "punjabi_text" in draft and len(draft["punjabi_text"]) > 10

    # 2. Get alert
    get_res = client.get(f"/api/alerts/{alert_id}")
    assert get_res.status_code == 200

    # 3. Approve alert with Official Bearer authentication (Human in the loop approval requirement)
    login_res = client.post("/api/auth/login", json={
        "email": "official@orca.punjab.gov.in",
        "password": "Official@123",
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    appr_payload = {
        "alert_id": alert_id,
        "approved_by": "Er. Harjit Kaur (SDMA Official)",
        "action": "APPROVE",
        "modification_notes": "Immediate broadcast authorized via SMS and PA system.",
    }
    appr_res = client.post(f"/api/alerts/{alert_id}/approve", json=appr_payload, headers=headers)
    assert appr_res.status_code == 200
    appr_data = appr_res.json()["data"]
    assert appr_data["status"] == "APPROVED"
    assert appr_data["action_taken"] == "APPROVE"
    assert appr_data["dispatch_results"] is not None
