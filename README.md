# ORCA-FloodGuard — Agentic AI Flood Early-Warning & Village Evacuation Advisor

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688.svg)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-Agentic_AI-orange.svg)](https://github.com/langchain-ai/langgraph)
[![React 18](https://img.shields.io/badge/React-18.3-61DAFB.svg)](https://react.dev/)
[![Leaflet](https://img.shields.io/badge/Leaflet-1.9-green.svg)](https://leafletjs.com/)
[![Tests Passing](https://img.shields.io/badge/Tests-95%2F95%20Passing-brightgreen.svg)]()

> **Mission**: An intelligent, multi-agent early warning and village evacuation advisor designed for high-risk floodplain villages in Punjab, India (Sutlej, Beas, Ravi, and Ghaggar river basins).

---

## 🌊 Overview

ORCA-FloodGuard combines **Agentic AI orchestration (LangGraph)**, **transparent deterministic hydrological rules**, and a **modern command-center UI (React + Leaflet + Recharts)** to empower disaster management authorities, district officials, and village residents before and during flood events.

### Core Capabilities:
- 🤖 **6 Autonomous Specialist Agents**: Location, Weather (IMD), River (CWC), Dam (BBMB), GIS & Evacuation, and Alert.
- 📐 **Deterministic Flood Risk Engine**: 24h, 48h, and 72h risk evaluation (`LOW`, `MODERATE`, `HIGH`, `CRITICAL`, `INSUFFICIENT_EVIDENCE`). LLM refines communication but **cannot override risk scores**.
- 🗺️ **Punjab Geospatial Command Map**: Interactive Leaflet maps rendering villages, CWC gauge sites, major dams, relief camps, and flood risk zones.
- 🗣️ **Bilingual Emergency Advisories**: Human-in-the-loop review of AI-generated alerts in English and Gurmukhi Punjabi (ਪੰਜਾਬੀ).
- 🔐 **PBKDF2 & JWT Role-Based Access Control**: Strict Citizen, District Official, and Emergency Admin security personas.
- 🛡️ **Operational Telemetry Integrity**: Strict honesty invariant — missing government telemetry is marked as `null`/`INSUFFICIENT_EVIDENCE` and never fabricated. Dual **DEMO** and **OPERATIONAL** modes.

---

## 🏛️ System Architecture

```
                                ┌───────────────────────────────────┐
                                │   ORCA Web UI (React 18 + Vite)   │
                                │ Leaflet Maps | Recharts | Bootstrap│
                                └─────────────────┬─────────────────┘
                                                  │ REST API / JWT
                                                  ▼
                                ┌───────────────────────────────────┐
                                │      FastAPI Gateway (/api)       │
                                │  Auth | RBAC | Providers | Routes │
                                └─────────────────┬─────────────────┘
                                                  │
                                                  ▼
                                ┌───────────────────────────────────┐
                                │   LangGraph Master Orchestrator   │
                                └─┬───────────────┬──────────────┬──┘
                                  │               │              │
                     ┌────────────┴─┐       ┌─────┴──────┐ ┌─────┴──────────┐
                     │Location Agent│       │Weather Agt │ │River Agent     │
                     └──────────────┘       └────────────┘ └────────────────┘
                                  │               │              │
                     ┌────────────┴─┐       ┌─────┴──────┐ ┌─────┴──────────┐
                     │Dam Agent     │       │GIS Evac Agt│ │Alert Agent     │
                     └──────────────┘       └────────────┘ └────────────────┘
                                                  │
                                                  ▼
                                ┌───────────────────────────────────┐
                                │  Deterministic Flood Risk Engine  │
                                │  (Strict Rules: 24h / 48h / 72h)  │
                                └─────────────────┬─────────────────┘
                                                  │
                                                  ▼
                                ┌───────────────────────────────────┐
                                │ LLM Advisory Refiner (Gemini/OAI) │
                                │  + Bilingual Human-in-the-Loop    │
                                └───────────────────────────────────┘
```

---

## 👥 Evaluation Personas & Demo Accounts

The system includes pre-configured evaluation accounts demonstrating full Role-Based Access Control (RBAC):

| Role | Username / Email | Password | Access Scope |
| :--- | :--- | :--- | :--- |
| **Emergency Admin** | `admin@orca.punjab.gov.in` | `Admin@123` | System settings, telemetry probe, threshold config, approval & dispatch |
| **District Official** | `official@orca.punjab.gov.in` | `Official@123` | Run village assessments, review & approve/reject bilingual alerts, verify routes |
| **Field Citizen** | `citizen@orca.punjab.gov.in` | `Citizen@123` | View public bulletins, submit geotagged flood reports, view nearby camps |

*Note: On the login page, use the **Quick Demo Fill** buttons to automatically fill credentials for any persona with one click.*

---

## 🚀 Quick Start Guide

### Option A: Local Development (Recommended for Evaluation)

#### 1. Start the Backend API
```bash
# Navigate to backend directory
cd backend

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Launch FastAPI server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
- API Documentation (Swagger): [http://localhost:8000/docs](http://localhost:8000/docs)
- Provider Health Status: [http://localhost:8000/api/providers/status](http://localhost:8000/api/providers/status)

#### 2. Start the Frontend Command Center
```bash
# Open a new terminal in the frontend directory
cd frontend

# Start the Vite development server
npm run dev
```
- Open Web Application: [http://localhost:5173](http://localhost:5173)

---

### Option B: Docker Compose Deployment

```bash
# From repository root
docker-compose up --build -d

# Check container status
docker-compose ps
```
- Frontend: [http://localhost:3000](http://localhost:3000)
- Backend: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🧪 Comprehensive Verification & Test Suite

The test suite covers:
- **Unit Tests**: Mathematical risk threshold rules, prompt validation, spatial distance calculations, password hashing & JWT encoding.
- **Agent Tests**: Specialist agent schemas, execution traces, evidence records, and error handlers.
- **Provider Tests**: IMD, CWC, and BBMB telemetry adapters, exponential backoff, health probes, and honest access rejection.
- **LangGraph Integration**: Full DAG execution, state transitions, conditional branching, and reducer safety.

Run all tests:
```bash
cd backend
venv\Scripts\python.exe -m pytest -v --tb=short -c pytest.ini tests
```
**Result**: 95 / 95 Passed (100% Pass Rate).

---

## 📄 Documentation Directory

- [Evaluator & Demo Guide](docs/DEMO_GUIDE.md) — Step-by-step evaluator walkthrough & scenario scripts.
- [System Architecture](docs/PROJECT_ARCHITECTURE.md) — Detailed agent coordination, DAG flow, and state schemas.
- [API Documentation](docs/API_DOCUMENTATION.md) — Complete REST endpoint catalog with sample payloads.
- [Data Sources & Providers](docs/data-sources.md) — IMD, CWC, and BBMB connector technical specifications.

---

## ⚖️ Safety & Telemetry Integrity Invariants

1. **Missing Data is Never Zero**: Missing or unavailable telemetry is stored as `null` and produces `INSUFFICIENT_EVIDENCE`. It is never converted to `0` or assumed safe.
2. **Deterministic Risk Authority**: LLMs assist in bilingual alert formulation but possess **zero authority** over risk classification.
3. **Mandatory Human-in-the-Loop**: High and Critical evacuation alerts are held in a `PENDING_APPROVAL` queue until authorized by an authenticated official.
4. **Authentic Government Connectivity**: Missing external API credentials report `BLOCKED_BY_ACCESS` or `CONFIGURED` honestly without fabricating simulated telemetry as live.
