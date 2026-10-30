# ORAC-FloodGuard Repository Structure

## Member 1 Ownership: Backend, Agentic AI & Database

```
backend/
├── app/
│   ├── main.py                     # FastAPI application entrypoint with middleware & exception handlers
│   ├── api/
│   │   ├── dependencies.py         # Common API dependencies (database session, auth verification)
│   │   └── routes/                 # REST API endpoints (11 router modules)
│   │       ├── health.py           # GET /api/health - Database & system health check
│   │       ├── flood.py            # POST /api/flood/assess, GET /assessments/{id}, GET /villages/{id}/outlook
│   │       ├── agents.py           # GET /api/agents/status/{run_id}, GET /api/agents/trace/{run_id}
│   │       ├── weather.py          # GET /api/weather/forecast
│   │       ├── river.py            # GET /api/river/stations, /readings/{id}, /status/{id}
│   │       ├── dam.py              # GET /api/dam/information
│   │       ├── gis.py              # GET /api/gis/location
│   │       ├── evacuation.py       # GET /api/evacuation/routes, /relief-centres
│   │       ├── replay.py           # POST /api/replay/start, GET /{id}, POST /{id}/step
│   │       ├── reports.py          # POST /api/reports/upload, GET /{id}, POST /{id}/review
│   │       └── alerts.py           # POST /api/alerts/draft, GET /{id}, POST /{id}/approve
│   │
│   ├── core/                       # Core system infrastructure
│   │   ├── config.py               # Pydantic Settings loaded from .env & environment
│   │   ├── logging.py              # Structured logging configuration
│   │   ├── security.py             # API Key security verification
│   │   ├── exceptions.py           # Domain exceptions
│   │   └── llm_factory.py          # Centralized LLM factory (Gemini, OpenAI, Deterministic Mock)
│   │
│   ├── schemas/                    # Pydantic v2 schemas and API contracts
│   │   ├── common.py               # BaseSchema, Coordinates, ApiResponse envelope
│   │   ├── location.py             # VillageLocation, LocationResolutionRequest/Response
│   │   ├── evidence.py             # EvidenceRecordSchema, EvidenceStatus, EvidenceQuality
│   │   ├── weather.py              # WeatherForecastData, WeatherAgentOutput
│   │   ├── river.py                # RiverStation, RiverReading, RiverAgentOutput
│   │   ├── dam.py                  # DamInformation, DamAgentOutput
│   │   ├── evacuation.py           # ReliefCentreSchema, EvacuationRouteSchema, GISEvacuationAgentOutput
│   │   ├── gis.py                  # GIS query parameters & response contracts
│   │   ├── flood.py / assessment.py# RiskLevel, RiskOutlook, FloodAssessmentRequest/Response
│   │   ├── agents.py / agent.py    # AgentName, AgentExecutionStatus, AgentExecutionTrace
│   │   ├── alerts.py / alert.py    # AlertChannel, AlertStatus, AlertDraftSchema, AlertApprovalRequest
│   │   ├── reports.py / report.py  # ReportStatus, ResidentReportCreate/Review/Response
│   │   └── replay.py               # HistoricalReplayStart/Step/Status contracts
│   │
│   ├── database/                   # Persistence Layer
│   │   ├── base.py                 # SQLAlchemy DeclarativeBase
│   │   ├── connection.py           # Engine & SessionLocal (SQLite fallback & PostgreSQL pooling)
│   │   ├── models.py               # 12 ORM entities: Village, DataSource, EvidenceRecord,
│   │   │                           # FloodAssessment, VillageRiskOutlook, AgentExecution,
│   │   │                           # ReliefCentre, EvacuationRoute, ResidentReport,
│   │   │                           # AlertDraft, AlertApproval, AuditLog
│   │   ├── repositories.py         # Clean repository data access pattern
│   │   └── init_db.py              # Database table creation and Punjab reference data seeding
│   │
│   ├── tools/                      # Data retrieval and integration tools
│   │   ├── geocoding_tool.py       # Punjab village resolution & bounding box checks
│   │   ├── weather_tool.py         # 24/48/72h precipitation forecast fetcher
│   │   ├── river_tool.py           # CWC station association & water level telemetry
│   │   ├── dam_tool.py             # BBMB / PSPCL reservoir level & spillway discharge
│   │   ├── elevation_tool.py       # NASA SRTM elevation and depression analysis
│   │   ├── relief_centre_tool.py   # Disaster shelter capacity & availability
│   │   ├── osm_tool.py             # OpenStreetMap infrastructure adapter
│   │   ├── routing_tool.py         # Route calculation & safety verification checking
│   │   ├── notification_tool.py    # Multi-channel notification adapter (human approval guarded)
│   │   ├── replay_tool.py          # 2023 Punjab monsoon deluge time-step replay engine
│   │   └── report_tool.py          # Resident ground observation validator
│   │
│   ├── agents/                     # Six specialist agents + BaseAgent
│   │   ├── base_agent.py           # Abstract BaseAgent with timing, status, and error tracing
│   │   ├── location_agent/         # Agent 1: Village & coordinate resolver
│   │   ├── weather_agent/          # Agent 2: 24/48/72h rainfall forecast agent
│   │   ├── river_agent/            # Agent 3: River stage & CWC gauge observer
│   │   ├── dam_agent/              # Agent 4: Reservoir level & release tracker
│   │   ├── gis_evacuation_agent/   # Agent 5: Topography, shelter & route planner
│   │   └── alert_agent/            # Agent 6: Multilingual advisory drafter
│   │
│   ├── services/                   # Business and domain services
│   │   ├── evidence_normalizer.py  # Evidence deduplication and canonical typing
│   │   ├── freshness_checker.py    # Observation age validation and STALE tagging
│   │   ├── evidence_validator.py   # Critical coverage & physical bounds validation gate
│   │   ├── risk_assessment.py      # Deterministic flood risk engine (24h/48h/72h rules)
│   │   ├── village_service.py      # Village CRUD and spatial resolution
│   │   ├── assessment_service.py   # End-to-end assessment persistence coordinator
│   │   ├── evacuation_service.py   # Route retrieval and shelter management
│   │   ├── alert_service.py        # Human approval lifecycle and alert dispatch
│   │   ├── report_service.py       # Citizen report upload and official review
│   │   ├── replay_service.py       # Chronological flood replay simulator
│   │   └── audit_service.py        # System audit trail logger
│   │
│   ├── orchestrator/               # LangGraph Agent Orchestration
│   │   ├── state.py                # MasterOrchestratorState TypedDict
│   │   ├── reducers.py             # Safe reducers for parallel agent evidence and traces
│   │   ├── nodes.py                # Graph nodes executing agents & gates
│   │   ├── router.py & edges.py    # Conditional routing and parallel fan-out/fan-in
│   │   ├── graph.py                # Compiled LangGraph DAG
│   │   └── workflow.py             # High-level assessment runner entrypoints
│   │
│   └── utils/                      # Helper utilities
│       ├── geo_utils.py            # Haversine distance & Punjab bounding box check
│       ├── timestamps.py           # ISO 8601 parsing & timezone-aware UTC helpers
│       └── units.py                # Cusecs-to-cumecs, feet-to-meters, mm-to-inches conversions
│
├── scripts/                        # Standalone utility and demonstration scripts
│   ├── init_db.py                  # Database setup and Punjab seeding
│   ├── load_sample_data.py         # Seed demo villages, shelters, and routes
│   ├── run_historical_replay.py    # Interactive CLI historical flood replay
│   └── verify_data_sources.py      # CLI script verifying all telemetry providers
│
├── tests/                          # Test suite (28 automated tests)
│   ├── conftest.py                 # Pytest fixtures, in-memory SQLite, FastAPI TestClient
│   ├── api/
│   │   ├── test_health.py          # Health check endpoint tests
│   │   └── test_routes.py          # End-to-end route tests for all 11 API modules
│   ├── unit/
│   │   ├── test_database.py        # ORM models and repository tests
│   │   └── test_evidence_and_risk.py # Deduplication, freshness, bounds, and risk rules
│   ├── agents/
│   │   └── test_specialist_agents.py # Independent unit tests for all 6 agents
│   └── integration/
│       └── test_orchestrator.py    # LangGraph workflow, routing, & DB persistence tests
│
├── .env.example                    # Sample environment variables
├── Dockerfile                      # Containerization instructions
├── pytest.ini                      # Pytest configuration
└── requirements.txt                # Python package dependencies
```

