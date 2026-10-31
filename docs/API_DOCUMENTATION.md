# ORCA-FloodGuard — API Documentation

Base URL: `http://localhost:8000/api`

---

## 1. Authentication Endpoints

### `POST /api/auth/login`
Authenticates a user and returns an HMAC-SHA256 JWT bearer token.
- **Request Body**:
  ```json
  {
    "email": "official@orca.punjab.gov.in",
    "password": "Official@123"
  }
  ```
- **Response**:
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "user": {
      "id": "usr-official-001",
      "email": "official@orca.punjab.gov.in",
      "full_name": "Sukhwinder Singh",
      "role": "OFFICIAL",
      "department": "Punjab Disaster Management Authority",
      "is_active": true
    }
  }
  ```

### `POST /api/auth/register`
Creates a new account (default role: `CITIZEN`).

### `GET /api/auth/me`
Returns current authenticated user profile. Requires `Authorization: Bearer <token>`.

### `GET /api/auth/demo-accounts`
Returns list of available evaluation personas and credentials for evaluation demonstrations.

---

## 2. Flood Assessment & Multi-Agent Orchestration

### `POST /api/flood/assess`
Executes the LangGraph multi-agent DAG workflow for a given village, horizon, and mode.
- **Request Body**:
  ```json
  {
    "village_name": "Gidderpindi",
    "district": "Jalandhar",
    "horizon_hours": 24,
    "mode": "DEMO"
  }
  ```
- **Response**:
  ```json
  {
    "assessment_id": "assess-20261031-001",
    "risk_level": "CRITICAL",
    "timestamp": "2026-10-31T01:00:00Z",
    "target_village": {
      "name": "Gidderpindi",
      "latitude": 31.185,
      "longitude": 75.142,
      "river_basin": "Sutlej",
      "distance_to_river_km": 0.4
    },
    "agent_telemetry": {
      "weather": { "rainfall_mm": 112.5, "rate_mm_h": 14.2 },
      "river": { "gauge_station": "Phillaur", "stage_m": 234.8, "warning_m": 232.0, "danger_m": 234.0, "status": "ABOVE_DANGER" },
      "dam": { "dam_name": "Bhakra", "discharge_cusecs": 58000, "capacity_percent": 94.2 },
      "evacuation": { "safe_camp": "Shahkot Senior Secondary School", "distance_km": 6.8, "route_verified": true }
    },
    "alert_advisory": {
      "english": "URGENT FLOOD ALERT: Sutlej river has breached danger level at Gidderpindi. Evacuate to Shahkot shelter.",
      "punjabi": "ਜ਼ਰੂਰੀ ਹੜ੍ਹ ਚੇਤਾਵਨੀ: ਗਿੱਦੜਪਿੰਡੀ ਵਿਖੇ ਸਤਲੁਜ ਦਰਿਆ ਖ਼ਤਰੇ ਦੇ ਨਿਸ਼ਾਨ ਤੋਂ ਪਾਰ ਹੋ ਗਿਆ ਹੈ। ਸ਼ਾਹਕੋਟ ਸ਼ੈਲਟਰ ਵੱਲ ਤੁਰੰਤ ਨਿਕਲੋ।"
    }
  }
  ```

---

## 3. Hydrological & Meteorological Telemetry

### `GET /api/weather/punjab`
Retrieves district-wise rainfall forecasts and observations across Punjab.

### `GET /api/river/gauges`
Returns real-time CWC river gauge stations along Sutlej, Beas, and Ravi basins.

### `GET /api/dam/reservoirs`
Returns current capacity, water level, and outflow for Bhakra, Pong, and Ranjit Sagar dams.

---

## 4. Evacuation & Spatial Relief

### `GET /api/evacuation/camps`
Lists designated relief camps, geographic coordinates, capacity, and current occupancy.

### `POST /api/evacuation/plan-route`
Calculates optimal safe route avoiding submerged road segments between a village and camp.

---

## 5. Alert Dispatch & Human-in-the-Loop Review

### `GET /api/alerts/`
Fetches all pending, approved, and dispatched flood bulletins.

### `POST /api/alerts/{alert_id}/approve`
**Role Required**: `OFFICIAL` or `ADMIN`.
Submits authorized approval for emergency broadcast dispatch.
- **Request Body**:
  ```json
  {
    "approver_id": "usr-official-001",
    "comments": "Verified stage telemetry with district CWC nodal officer."
  }
  ```

### `POST /api/alerts/{alert_id}/reject`
Rejects or requests modifications to an alert draft.

---

## 6. Citizen Community Reports

### `GET /api/reports/`
Returns citizen-submitted flood observations with geolocation and verification flags.

### `POST /api/reports/`
Submits a geotagged resident report with water depth and road passability status.

---

## 7. Telemetry Providers & System Status

### `GET /api/providers/status`
Returns connectivity, authentication, and health status of all 3 external integrations (`IMD`, `CWC`, `BBMB`).

### `GET /api/providers/{provider_name}/health`
Executes an on-demand active probe to test upstream reachability.

