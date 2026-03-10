# Urban Flood Intelligence Engine (UFIE)

AI-driven GIS platform for urban flood risk prediction and management.

## Overview

UFIE (Urban Flood Intelligence Engine) is a comprehensive geospatial analytics platform that predicts urban flooding, identifies 2500+ micro-hotspots across city wards, generates Pre-Monsoon Readiness Scores for every ward, and provides AI-powered insights through an integrated copilot. It combines machine learning, GIS analysis, and real-time simulation to help municipal authorities make data-driven decisions for flood preparedness and infrastructure planning.

## Features

1. **Flood Hotspot Detection** -- Identifies and classifies 2500+ micro-hotspots with severity ratings (Critical, High, Moderate, Low) using elevation, drainage, and historical data.
2. **Pre-Monsoon Readiness Score** -- Composite 0-100 score for each ward across 5 dimensions: drainage capacity, emergency infrastructure, hotspot density, rainfall vulnerability, and pump availability.
3. **AI Copilot** -- Natural language query interface powered by ChatGPT and Gemini for flood risk analysis, policy recommendations, and report generation.
4. **Rainfall Simulation Engine** -- Simulates flood impact across wards at configurable rainfall intensities (10-100+ mm/hr) with progressive multi-intensity analysis.
5. **Interactive GIS Map** -- Leaflet-based map with ward boundaries, hotspot markers, drainage networks, pump stations, and clustered views.
6. **Ward Risk Rankings** -- Ranked list of all wards by readiness score with drill-down into individual scoring dimensions.
7. **Infrastructure Gap Analysis** -- Identifies missing or insufficient drainage, pump stations, and emergency infrastructure per ward with prioritized recommendations.
8. **Real-Time Risk Alerts** -- Generates alerts for wards falling below readiness thresholds with severity classification.
9. **Flood Prediction Model** -- ML-based prediction of flood probability at any lat/lng coordinate using XGBoost trained on terrain and infrastructure features.
10. **Dashboard Analytics** -- Summary statistics, charts, and KPIs for city-wide flood preparedness at a glance.
11. **Drainage Network Visualization** -- GeoJSON overlay of the city drainage network with capacity indicators.
12. **Historical Rainfall Analysis** -- Time-series visualization of rainfall patterns to identify trends and anomalies.
13. **Export and Reporting** -- Generate downloadable preparedness reports and simulation results for stakeholder briefings.

## Architecture

```
ufie/
├── backend/          # Python FastAPI server
│   ├── app/
│   │   ├── api/routes/    # REST API endpoints
│   │   ├── models/        # Pydantic schemas & DB models
│   │   ├── services/      # Business logic
│   │   │   ├── gis_analysis.py
│   │   │   ├── ward_scoring.py
│   │   │   ├── rainfall_simulation.py
│   │   │   ├── infrastructure_gap.py
│   │   │   └── ai_copilot.py
│   │   └── ml/            # Machine learning
│   │       ├── features.py
│   │       └── train_model.py
│   └── data/sample/       # Generated sample data
├── frontend/         # React + TypeScript dashboard
│   └── src/
│       ├── components/
│       │   ├── map/       # Leaflet map components
│       │   ├── charts/    # Recharts visualizations
│       │   ├── ai/        # AI Copilot panel
│       │   ├── layout/    # Header, Sidebar
│       │   └── dashboard/ # Analytics, Simulation, Alerts
│       ├── services/      # API client
│       ├── hooks/         # Custom React hooks
│       ├── types/         # TypeScript definitions
│       └── utils/         # Helper functions
└── docker-compose.yml
```

## Tech Stack

- **Backend:** Python, FastAPI, GeoPandas, Scikit-learn, XGBoost
- **Frontend:** React, TypeScript, Leaflet, Recharts, Tailwind CSS
- **Database:** PostgreSQL + PostGIS
- **AI:** OpenAI GPT-4, Google Gemini (with built-in fallback)
- **DevOps:** Docker, Docker Compose

## Quick Start

### Option 1: Docker Compose (Recommended)

```bash
cd ufie
cp backend/.env.example backend/.env
# Optional: Add OPENAI_API_KEY and GEMINI_API_KEY to .env
docker-compose up --build
```

Access the application:
- **Frontend:** http://localhost:3000
- **API Docs:** http://localhost:8000/docs

### Option 2: Manual Setup

#### Backend

```bash
cd ufie/backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
python -c "from data.sample.generate_sample_data import generate_all_data; generate_all_data('data/sample')"
uvicorn app.main:app --reload
```

#### Frontend

```bash
cd ufie/frontend
npm install
npm run dev
```

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/dashboard/summary` | GET | Dashboard statistics |
| `/api/hotspots/` | GET | Flood hotspots (filterable) |
| `/api/hotspots/summary` | GET | Hotspot summary stats |
| `/api/hotspots/clusters` | GET | Clustered hotspots |
| `/api/flood-prediction/` | POST | Predict flood risk at location |
| `/api/ward-score/` | GET | Ward readiness scores |
| `/api/ward-score/rankings` | GET | Ward rankings |
| `/api/ward-score/alerts` | GET | Risk alerts |
| `/api/simulate-rainfall/` | POST | Rainfall simulation |
| `/api/simulate-rainfall/progressive` | GET | Multi-intensity simulation |
| `/api/ai-query/` | POST | AI copilot query |
| `/api/infrastructure/gaps` | GET | Infrastructure gaps |
| `/api/infrastructure/recommendations` | GET | Improvement recommendations |
| `/api/dashboard/wards` | GET | Ward boundaries GeoJSON |
| `/api/dashboard/drainage` | GET | Drainage network GeoJSON |
| `/api/dashboard/pumps` | GET | Pump stations GeoJSON |
| `/api/dashboard/rainfall` | GET | Historical rainfall data |

## AI Copilot

The AI Copilot integrates ChatGPT and Gemini for:

- **Flood risk analysis and reasoning** -- Understand why specific wards are at risk and what factors contribute most.
- **Policy and infrastructure recommendations** -- Get actionable suggestions for drainage upgrades, pump installations, and emergency preparedness.
- **Preparedness report generation** -- Auto-generate comprehensive pre-monsoon readiness reports for municipal stakeholders.
- **Natural language query answering** -- Ask questions in plain English about flood risk, ward scores, and infrastructure status.

Works with or without API keys (built-in intelligence as fallback).

## Sample Queries for AI Copilot

- "Which wards will flood if rainfall exceeds 60mm/hr?"
- "What infrastructure upgrades reduce risk?"
- "Generate a pre-monsoon preparedness report"
- "What is the readiness score breakdown?"
- "Compare drainage capacity across the top 5 at-risk wards"
- "What is the flood probability at coordinates 28.65, 77.23?"

## Data Sources

The platform accepts:

- **GeoJSON files** for ward boundaries, hotspots, and drainage networks
- **Shapefiles** for GIS data import
- **DEM elevation grids** for terrain analysis
- **Historical rainfall datasets** for trend analysis and model training

Sample data is auto-generated for Delhi with 2700+ hotspots across 30 wards, complete with drainage networks, pump stations, and historical rainfall records.

## Pre-Monsoon Readiness Score

Composite 0-100 score computed across 5 dimensions:

| Dimension | Weight | Description |
|---|---|---|
| Drainage Capacity Index | 0-25 | Adequacy of drainage infrastructure relative to ward area and rainfall volume |
| Emergency Infrastructure Coverage | 0-20 | Availability of shelters, medical facilities, and emergency access routes |
| Flood Hotspot Density | 0-25 | Inverse of hotspot concentration -- fewer hotspots means higher score |
| Rainfall Vulnerability | 0-15 | Historical rainfall patterns and terrain susceptibility |
| Pump Station Availability | 0-15 | Coverage and capacity of pump stations within the ward |

### Score Categories

| Range | Category | Action |
|---|---|---|
| 0-30 | Critical Risk | Immediate intervention required |
| 31-60 | Moderate Risk | Targeted upgrades needed |
| 61-80 | Prepared | Minor improvements recommended |
| 81-100 | Resilient | Maintenance and monitoring |

## License

MIT
