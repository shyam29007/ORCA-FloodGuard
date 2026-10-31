# ORCA-FloodGuard — System & Agent Architecture

## 1. System Overview

**ORCA-FloodGuard** is an Agentic AI-powered flood early-warning and village evacuation advisor purpose-built for the vulnerable floodplain villages along the Sutlej, Beas, and Ravi river basins in Punjab, India.

```
                              ┌──────────────────────────────────┐
                              │     ORCA Web UI (React + Vite)   │
                              │ Leaflet Maps | Recharts | Alerts │
                              └────────────────┬─────────────────┘
                                               │ REST API / JWT
                                               ▼
                              ┌──────────────────────────────────┐
                              │     FastAPI Gateway (/api)       │
                              │  Auth | RBAC | Providers | Routes │
                              └────────────────┬─────────────────┘
                                               │
                                               ▼
                              ┌──────────────────────────────────┐
                              │    LangGraph Master Orchestrator │
                              └─┬──────────────┬──────────────┬──┘
                                │              │              │
                    ┌───────────┴─┐      ┌─────┴──────┐ ┌─────┴──────────┐
                    │Location Agt │      │Weather Agt │ │River Agent      │
                    └─────────────┘      └────────────┘ └─────────────────┘
                                │              │              │
                    ┌───────────┴─┐      ┌─────┴──────┐ ┌─────┴──────────┐
                    │Dam Agent    │      │GIS Evac Agt│ │Alert Agent      │
                    └─────────────┘      └────────────┘ └─────────────────┘
                                               │
                                               ▼
                              ┌──────────────────────────────────┐
                              │ Deterministic Flood Risk Engine  │
                              │ (Strict Rules: 24h / 48h / 72h)  │
                              └────────────────┬─────────────────┘
                                               │
                                               ▼
                              ┌──────────────────────────────────┐
                              │ LLM Advisory Refiner (Gemini/OAI)│
                              │  + Bilingual Human-in-the-Loop   │
                              └──────────────────────────────────┘
```

---

## 2. Six Specialist Agents

### Agent 1: Location Agent
- **Responsibility**: Resolves target village/settlement names, resolves exact latitude/longitude, links river basin (Sutlej, Beas, Ravi, Ghaggar), and computes spatial distance to nearest riverbank.
- **Fail-Safe**: If coordinates or river basins cannot be confidently resolved, halts downstream hydrological calculations and raises a spatial evidence alert.

### Agent 2: Weather Agent
- **Responsibility**: Queries Indian Meteorological Department (IMD) telemetry and numerical weather prediction models for 24h, 48h, and 72h accumulated rainfall forecasts and rainfall rates (mm/h).
- **Fail-Safe**: In `OPERATIONAL` mode, missing rainfall is strictly recorded as `None`/`null` without defaulting to zero.

### Agent 3: River Agent
- **Responsibility**: Fetches stage and discharge telemetry from Central Water Commission (CWC) hydro-meteorological stations (e.g., Phillaur, Harike, Gidderpindi).
- **Metrics**: Compares gauge stage against official Warning Level (WL) and Danger Level (DL), evaluating trajectory over 3-6 hour windows.

### Agent 4: Dam Agent
- **Responsibility**: Tracks major upstream reservoir levels, inflows, and spillway discharge (in cusecs) for Bhakra Dam (Govind Sagar), Pong Dam (Maharana Pratap Sagar), and Ranjit Sagar Dam.
- **Metrics**: Identifies critical reservoir capacity percent (>90%) and sudden spillway surges into downstream tributaries.

### Agent 5: GIS & Evacuation Agent
- **Responsibility**: Computes terrain elevation, digital elevation model clearance, safe high-ground zones, and candidate evacuation routes to designated relief shelters (schools, colleges, community centers).
- **Verification Invariant**: Routes are explicitly marked with clearance safety status. Unverified or submerged roads are flagged as unsafe.

### Agent 6: Alert Agent
- **Responsibility**: Generates bilingual advisories in English and Gurmukhi Punjabi (ਪੰਜਾਬੀ).
- **Human-in-the-Loop Gate**: All critical alerts require explicit review and approval by an authorized District Emergency Officer or Admin before broadcast.

---

## 3. Deterministic Flood Risk Engine

ORCA-FloodGuard strictly separates **AI reasoning & communication** from **safety-critical risk scoring**. The LLM (Gemini or OpenAI) is restricted to refining bilingual advisories and **cannot override deterministic risk levels**:

| Risk Tier | Hydrological & Meteorological Criteria | Action Trigger |
| :--- | :--- | :--- |
| **CRITICAL** | River Stage $\ge$ Danger Level OR Upstream Dam Discharge $> 50,000$ cusecs with Heavy Rain ($> 100$ mm) | Immediate Evacuation Order drafted |
| **HIGH** | River Stage $\ge$ Warning Level OR Dam Discharge $> 30,000$ cusecs OR Extreme Rain ($> 64.5$ mm) | Evacuation Advisory drafted, emergency teams on standby |
| **MODERATE** | Upstream discharge elevated OR Moderate Rainfall ($15-64$ mm) with saturated basin | Flood Watch issued, vulnerable cattle/assets relocated |
| **LOW** | All river stages below warning, dam release normal, rainfall $< 15$ mm | Normal Monitoring |
| **INSUFFICIENT_EVIDENCE** | Key hydrological gauge or rainfall data missing or unverified | Emergency validation prompted; NO false negative assumption |

---

## 4. Live Telemetry Connector Architecture

Located in `backend/app/integrations/`:
1. **BaseProvider**: Configurable asynchronous HTTPX client featuring bounded exponential backoff, jitter, timeouts, and sanitized logging.
2. **IMDWeatherProvider**: Fetches precipitation forecasts and district observations.
3. **CWCRiverProvider**: Fetches gauge stage and flood threshold levels.
4. **BBMBDamProvider**: Monitors Bhakra & Beas reservoir storage and spillway discharge.
5. **Provider Health Probe**: Evaluates connection states (`CONFIGURED`, `AUTHENTICATED`, `CONNECTED`, `VALID_RESPONSE`, `LIVE_DATA_AVAILABLE`, `BLOCKED_BY_ACCESS`).

