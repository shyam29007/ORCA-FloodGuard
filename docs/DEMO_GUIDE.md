# ORCA-FloodGuard — Evaluator & Demo Guide

Welcome to the **ORCA-FloodGuard** Evaluator Guide. This document provides step-by-step instructions to run, verify, and demonstrate the entire platform for college hackathons, project evaluations, and emergency response demonstrations.

---

## 1. Quick Start (Zero-Setup Evaluation)

### Terminal 1: Backend API (Port 8000)
```bash
# From repository root
cd backend
# Activate Python 3.11 virtual environment
venv\Scripts\activate       # Windows PowerShell / CMD
# or source venv/bin/activate  # Linux / macOS

# Start FastAPI server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
- Swagger Interactive Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Provider Status API: [http://localhost:8000/api/providers/status](http://localhost:8000/api/providers/status)

### Terminal 2: Frontend Command Center (Port 5173 / 3000)
```bash
# From repository root
cd frontend
npm run dev
```
- Open in Browser: [http://localhost:5173](http://localhost:5173)

---

## 2. Evaluation Personas & Credentials

The platform includes pre-seeded evaluation accounts demonstrating Role-Based Access Control (RBAC):

| Role | Username / Email | Password | Allowed Capabilities |
| :--- | :--- | :--- | :--- |
| **Emergency Admin** | `admin@orca.punjab.gov.in` | `Admin@123` | Full access: provider re-probing, threshold audit, system settings, approval & dispatch |
| **District Official** | `official@orca.punjab.gov.in` | `Official@123` | Assess floods, review and approve/reject bilingual alerts, verify evacuation routes |
| **Field Citizen** | `citizen@orca.punjab.gov.in` | `Citizen@123` | View public bulletins, submit geotagged community reports, inspect relief camps |

> **Pro Tip**: On the Login screen, click any of the **Quick Demo Fill** buttons to immediately load credentials for that role.

---

## 3. Demo Mode vs Operational Mode Switch

Located in the top navigation bar, the **Mode Switcher** controls telemetry evaluation rules:
- **DEMO Mode (Gold Badge)**: Uses validated simulated flood telemetry scenarios (2023 Punjab floods) to demonstrate agent reasoning, multi-horizon risk scoring (24h/48h/72h), and bilingual alert generation.
- **OPERATIONAL Mode (Teal Badge)**: Strict live telemetry mode. Connects to real-time government endpoints. If government credentials are missing or endpoints are unreachable, safety invariant #1 strictly activates: missing data is represented as `null`/`INSUFFICIENT_EVIDENCE` and **never fabricated**.

---

## 4. Suggested 5-Minute Evaluator Walkthrough

### Step 1: Real-time Multi-Agent Flood Assessment
1. Navigate to **Flood Assessment** (`/assessment`).
2. Select target village: **Gidderpindi (Jalandhar / Sutlej Basin)**.
3. Keep Horizon as **24 Hours**, Mode as **DEMO**.
4. Click **Run Multi-Agent Assessment**.
5. Observe:
   - **LangGraph Multi-Agent Execution**: Visual timeline showing Location Agent, Weather Agent, River Agent, Dam Agent, and GIS Agent executing in parallel.
   - **Deterministic Risk Engine**: Computed risk score (e.g. `HIGH` or `CRITICAL`).
   - **Bilingual Alert Draft**: AI-refined advisory in both English and Punjabi (Gurmukhi: ਪੰਜਾਬੀ).
   - **Interactive Leaflet Map**: Shows the selected village pin, nearest CWC station, upstream dams, and relief shelter.

### Step 2: Interactive Punjab Flood Map
1. Navigate to **Flood Map** (`/map`).
2. Explore interactive layers:
   - **Dams Layer**: Bhakra, Pong, Ranjit Sagar (click to see current level vs max reservoir limit).
   - **CWC River Gauges Layer**: Phillaur, Harike Barrage, Gidderpindi, Madhopur (stage vs warning/danger levels).
   - **Evacuation Camps Layer**: Govt Sen Sec School Shahkot, DAV College Jalandhar, Anandpur Sahib Camp.
3. Filter by Risk Tier (Critical, High, Moderate, Low).

### Step 3: Human-in-the-Loop Alert Management
1. Navigate to **Alerts** (`/alerts`).
2. Switch persona to **District Official** or **Emergency Admin**.
3. Locate a **Pending Approval** alert draft.
4. Click **Review & Approve**:
   - Inspect the dual English & Punjabi message draft.
   - Review affected demographics and village coordinates.
   - Click **Approve & Broadcast** or **Reject Draft** with audit reason.
   - Confirm status transitions to **Dispatched**.

### Step 4: Evacuation Route & Camp Planning
1. Navigate to **Evacuation** (`/evacuation`).
2. Inspect candidate evacuation routes from vulnerable villages to designated relief camps.
3. Review terrain clearance, road flood risk, capacity, and route safety validation status.

### Step 5: Live Telemetry Provider & Agent Health
1. Navigate to **System Status** (`/system-status`).
2. Inspect the live status of all 3 external telemetry adapters:
   - **IMD Weather**: Indian Meteorological Department API connector.
   - **CWC River**: Central Water Commission hydrological telemetry.
   - **BBMB Dam**: Bhakra Beas Management Board reservoir monitor.
3. Note the explicit honest status: `CONFIGURED` / `BLOCKED_BY_ACCESS` (preserving production safety invariants without fabricating fake government keys).
4. Review the health matrix of all 6 specialist agents and LangGraph orchestrator.

---

## 5. Docker Deployment Execution

To run the entire system inside isolated production containers:
```bash
# Build and run with Docker Compose
docker-compose up --build -d

# Check running containers
docker-compose ps

# Access frontend at http://localhost:3000
# Access backend at http://localhost:8000
```

