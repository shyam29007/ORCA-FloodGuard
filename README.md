# ORAC-FloodGuard: Backend, Agentic AI & Database

**ORAC-FloodGuard** is an Agentic AI-powered Flood Early-Warning and Village Evacuation Advisor designed for vulnerable floodplain villages in Punjab, India (e.g., Sutlej, Beas, and Ravi basins).

This component represents the complete backend implementation (**Member 1**), featuring:
1. **FastAPI REST Backend**: High-performance asynchronous API endpoints with comprehensive Pydantic v2 schemas.
2. **LangGraph Agent Orchestration**: A directed acyclic graph orchestrating six specialist agents with parallel telemetry retrieval, safe reducers, and conditional routing.
3. **Six Specialist Agents**:
   - **Agent 1: Location Agent** (Resolves village name, coordinates, river basin, and distance to river).
   - **Agent 2: Weather Agent** (Gathers 24h, 48h, and 72h precipitation forecasts).
   - **Agent 3: River Agent** (Associates CWC stations, monitors river stage, warning, and danger levels).
   - **Agent 4: Dam Agent** (Tracks reservoir storage and spillway discharge from Bhakra, Pong, and Ranjit Sagar dams).
   - **Agent 5: GIS & Evacuation Agent** (Calculates terrain elevation, identifies shelters, and generates candidate routes with strict verification status).
   - **Agent 6: Alert Agent** (Drafts bilingual English & Punjabi advisories requiring human approval before dispatch).
4. **Deterministic Flood-Risk Engine**: Python-based transparent decision rules across 24h, 48h, and 72h horizons (LOW, MODERATE, HIGH, CRITICAL, or INSUFFICIENT_EVIDENCE).
5. **Centralized LLM Factory**: Single configured LLM provider (Google Gemini or OpenAI) with deterministic fallback when offline or unconfigured. LLM refines communication but **cannot calculate or override risk levels**.
6. **Dual Database Support**: SQLite fallback for zero-configuration local development and PostgreSQL/PostGIS support for production.

---

## 1. Getting Started

### Prerequisites
- Python 3.11+
- Virtual environment tool (`venv` or `virtualenv`)

### Installation
1. Clone the repository and navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Linux/macOS:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy environment configuration:
   ```bash
   cp .env.example .env
   ```

### Database Initialization & Sample Data Seeding
Run the initialization script to create tables and seed baseline Punjab flood-monitoring geography (Gidderpindi, Shahkot, Phillaur, Harike, Anandpur Sahib, Firozpur Rural):
```bash
python scripts/load_sample_data.py
```

### Running the API Server
Start the Uvicorn server:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
- Interactive Swagger API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
- Alternative ReDoc Documentation: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- System Health Check: [http://localhost:8000/api/health](http://localhost:8000/api/health)

---

## 2. Environment Variables

Configure the following variables in `backend/.env`:

| Variable | Description | Default |
| :--- | :--- | :--- |
| `APP_ENV` | Application environment (`development`, `test`, `production`) | `development` |
| `DATABASE_MODE` | Database type (`sqlite` or `postgres`) | `sqlite` |
| `DATABASE_URL` | Database connection string | `sqlite:///./orac_floodguard.db` |
| `LLM_PROVIDER` | Language model provider (`gemini`, `openai`, `mock`) | `gemini` |
| `LLM_MODEL` | Language model identifier | `gemini-1.5-flash` |
| `GEMINI_API_KEY` | Google Gemini API key (optional; defaults to deterministic bilingual templates if empty) | |
| `WEATHER_API_BASE_URL` | Base URL for external weather provider (optional) | |
| `RIVER_API_BASE_URL` | Base URL for external river gauge provider (optional) | |
| `DAM_API_BASE_URL` | Base URL for external dam telemetry provider (optional) | |
| `REQUEST_TIMEOUT` | External HTTP client timeout in seconds | `20` |
| `LOG_LEVEL` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `INFO` |

---

## 3. Workflow Architecture

```
START
  │
Validate Input
  │
Location Agent (Resolves village coordinates & river basin)
  │
Conditional Router
  ├──> Weather Agent ──────────┐
  ├──> River Agent ────────────┼─ (Parallel Evidence Retrieval)
  ├──> Dam Agent ──────────────┤
  └──> GIS & Evacuation Agent ─┘
  │
Evidence Normalization (Deduplication & standard unit coercion)
  │
Evidence Validation Gate (Freshness, bounds & critical parameter coverage)
  │
Deterministic Risk Assessment (24h / 48h / 72h independent outlooks)
  │
Alert Agent (Drafts bilingual English & Punjabi advisory)
  │
Database Persistence (Stores assessment, outlooks, evidence & execution traces)
  │
END
```

---

## 4. API Endpoints

### Health
- `GET /api/health`: Health status, DB connection, and provider status.

### Flood Assessment
- `POST /api/flood/assess`: Triggers LangGraph multi-agent assessment for a village.
- `GET /api/flood/assessments/{assessment_id}`: Retrieves complete assessment with outlooks and evidence.
- `GET /api/flood/villages/{village_id}/outlook`: Retrieves latest 24/48/72h outlook for a village.

### Agent Execution
- `GET /api/agents/status/{run_id}`: High-level execution status of an assessment run.
- `GET /api/agents/trace/{run_id}`: Granular execution timing, inputs, and outputs of each specialist agent.

### Telemetry & Infrastructure
- `GET /api/weather/forecast`: 24h, 48h, 72h precipitation forecasts.
- `GET /api/river/stations`: List CWC river gauge stations in Punjab.
- `GET /api/river/readings/{station_id}`: Latest gauge reading.
- `GET /api/river/status/{station_id}`: Warning & danger threshold status.
- `GET /api/dam/information`: Telemetry for Bhakra, Pong, and Ranjit Sagar dams.
- `GET /api/gis/location`: Elevation profile and floodplain depression assessment.
- `GET /api/evacuation/routes`: Designated evacuation corridors with verification tags.
- `GET /api/evacuation/relief-centres`: Active disaster relief camps and capacities.

### Historical Replay
- `POST /api/replay/start`: Initialize a historical replay (e.g. July 2023 Punjab floods).
- `GET /api/replay/{replay_id}`: Query current simulation time step and risks.
- `POST /api/replay/{replay_id}/step`: Advance simulation by chronological steps.

### Resident Ground Reports
- `POST /api/reports/upload`: Citizen submission of localized flooding.
- `GET /api/reports/{report_id}`: Query submitted report.
- `POST /api/reports/{report_id}/review`: Official validation/verification workflow.

### Warnings & Human-in-the-Loop Approval
- `POST /api/alerts/draft`: Generate advisory draft.
- `GET /api/alerts/{alert_id}`: Inspect alert draft text and target channels.
- `POST /api/alerts/{alert_id}/approve`: **Mandatory human approval gate** authorizing dissemination.

---

## 5. Running Automated Tests

Run the complete 28-test test suite:
```bash
pytest -c backend/pytest.ini backend/tests
```

---

## 6. Integration Guide for Teammates

### For Member 2 (External Provider Adapters):
1. **Weather Adapters**: Point your adapter to `GET /api/weather/forecast` or set `WEATHER_API_BASE_URL` in `.env`. Return JSON containing `rain_24h_mm`, `rain_48h_mm`, `rain_72h_mm`.
2. **River Gauges**: Feed CWC live station data matching station IDs (`CWC_SUTLEJ_PHILLAUR`, `CWC_SUTLEJ_LOHIAN`, `CWC_SUTLEJ_ROPAR`, `CWC_HARIKE_BARRAGE`, `CWC_SUTLEJ_HUSSAINIWALA`) with `water_level_m` and `discharge_cusecs`.
3. **Dam Telemetry**: Supply live releases for `BBMB_BHAKRA_DAM`, `BBMB_PONG_DAM`, `PSPCL_RANJIT_SAGAR_DAM`.

### For Member 3 (Frontend React UI):
1. **Triggering Assessment**: Call `POST /api/flood/assess` with `{ "village_name": "Gidderpindi" }`.
2. **Displaying Outlooks**: Read `data.outlooks["24h"]`, `data.outlooks["48h"]`, `data.outlooks["72h"]`.
3. **Agent Status & Trace**: Poll `GET /api/agents/trace/{run_id}` to render the multi-agent reasoning steps, timings, and logs in the UI.
4. **Interactive Map**: Use `GET /api/evacuation/routes` and `GET /api/evacuation/relief-centres` to render evacuation paths and high-ground shelters on the map.
5. **Alert Center**: Display pending alerts from `GET /api/alerts/pending` and allow emergency officers to click **Approve** via `POST /api/alerts/{alert_id}/approve`.

