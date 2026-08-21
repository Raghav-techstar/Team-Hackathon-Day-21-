# Shipment Operations Control Tower — Requirements

## 1. Overview

Internal dashboard for ops managers to view live shipment status, on-time delivery, and data quality issues from one place instead of three spreadsheets.

The service is a FastAPI backend that serves cleaned shipment data from CSV/staging sources, exposes status and data-quality endpoints, includes OAuth2 (password/bearer token) authentication, a Claude-powered AI chat assistant, and serves a static HTML/JS frontend for the dashboard itself.

## 2. Setup

### Prerequisites

- Python 3.11+ and pip
- A virtual environment tool (venv)
- PostgreSQL (used by `postgres_loader.py` / SQLAlchemy + psycopg for the loading pipeline)
- An Anthropic API key (required for the `/ai/chat` endpoint)

### Install Dependencies

```bash
# clone / cd into the project
cd Team-Hackathon-Day-21-

# create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# install requirements
pip install -r requirements.txt
```

`requirements.txt`: pandas, ruff, sqlalchemy, psycopg[binary], python-dotenv, fastapi, uvicorn, pydantic, python-multipart, anthropic

### Environment Variables

Create a `.env` file in the project root (already git-ignored) with:

```
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

`app/ai_service.py` loads this at import time and raises a `RuntimeError` on startup if the key is missing.

### Prepare the Data

- `raw_shipments.csv` is the source input for the clean/load pipeline.
- `shipment_cleaning.py` applies the DQ rules (carrier, status, freight cost, shipment ID, date format) and produces `Clean_Shipments.csv` and `Rejected_Shipments.csv` in `data/`.
- `postgres_loader.py` loads the cleaned data into a PostgreSQL `shipments_clean` staging table for downstream/database use.
- The FastAPI endpoints below read directly from the CSVs in `data/` via `app/data_loader.py`.

## 3. Running Locally

### Step 1 — Run the cleaning pipeline

```bash
python shipment_cleaning.py
```

Generates `data/Clean_Shipments.csv` and `data/Rejected_Shipments.csv` from `data/raw_shipments.csv`.

### Step 2 — (Optional) Load into PostgreSQL

```bash
python postgres_loader.py
```

Loads the cleaned data into the `shipments_clean` staging table in PostgreSQL.

### Step 3 — Start the API server

```bash
uvicorn app.main:app --reload --port 8000
```

The FastAPI app also mounts the `frontend/` directory as a static site at the root path, so the dashboard UI loads directly from the same server.

### Step 4 — Open the app

- Dashboard UI: `http://localhost:8000/`
- Swagger / interactive API docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Step 5 — Authenticate

All `/status/*` and `/ai/chat` endpoints require an OAuth2 bearer token. Obtain one from `POST /token` using the demo credentials below, then use it as the Bearer token for subsequent requests (Swagger UI's "Authorize" button handles this automatically).

```
POST /token
Content-Type: application/x-www-form-urlencoded

username=admin&password=admin123

# response
{
  "access_token": "admin",
  "token_type": "bearer"
}
```

Demo credentials are hardcoded in `app/auth.py` (username: `admin`, password: `admin123`) for MVP purposes.

## 4. Endpoints

| Method & Path | Auth | Description |
|---|---|---|
| `POST /token` | None | Exchange username/password for an OAuth2 bearer token. |
| `GET /status/summary` | Bearer | Aggregate KPIs: total shipments, on-time rate, average freight cost. |
| `GET /status/shipments` | Bearer | Filterable shipment records. Query params: `carrier`, `status`. |
| `GET /status/dq-report` | Bearer | Real PASS/FAIL data-quality report with per-check failures. |
| `POST /ai/chat` | Bearer | Claude-powered assistant; answers questions about live shipment data and the project. |
| `GET /` | None | Serves the static dashboard frontend (`frontend/index.html`, `app.js`, `style.css`). |
| `GET /docs` | None | Auto-generated Swagger UI. |
| `GET /redoc` | None | Auto-generated ReDoc API reference. |

Full request/response schemas for `/status/summary`, `/status/shipments`, and `/status/dq-report` are in Section 10 below (API Contract). The `/ai/chat` request/response and configuration details are in Section 10b (AI Assistant API).

## 5. Architecture (Locked)

```
raw_shipments.csv
        |
Clean and load pipeline (profile, standardize, log)
        |
shipments_clean (staging table)
        |
   -----------------------------------------------------
   |                |                  |                |
/status/summary  /status/shipments  /status/dq-report  /ai/chat
   |                                                     |
   |                                              (calls Anthropic
   |                                               Claude API with
   |                                               live data as
   |                                               context)
   -----------------------------------------------------
        |
Swagger UI / demo (live judge walkthrough)
```

`/ai/chat` is a fourth consumer of `shipments_clean`, alongside the three status endpoints. On each call it re-reads the current cleaned/rejected data and dq-report result, and is the only endpoint that also calls an external service (the Anthropic Claude API) to generate its response.

## 6. Raw Data Schema — `raw_shipments.csv`

| Field | Type | Notes |
|---|---|---|
| shipment_id | string | e.g. SH00001, must be unique and not null |
| carrier | string | DHL, BLUEDART, FEDEX only |
| ship_date | string | accepted formats: MM/DD/YYYY, MM-DD-YYYY |
| status | string | see DQ mapping below |
| origin | string | city name |
| destination | string | city name |
| freight_cost | float | must be > 0 |
| Expected Delivery Date | string | date |
| Delivered Date | string | date |

## 7. Data Quality Rules (Reject / Accept Logic)

### Carrier

Accept only: **DHL**, **BLUEDART**, **FEDEX**. Any other carrier value → **reject**.

### Status (raw → normalized)

| Raw Value | Normalized Value |
|---|---|
| Delayed | Delayed |
| DELIVERED | Delivered |
| In Transit | In Transit |
| IN_TRANSIT | In Transit |
| in-transit | In Transit |
| pending | Pending |
| *(blank)* | Accepted |

Any raw status value not in the table above → **reject**.

### Freight Cost

`freight_cost <= 0` → **reject**.

### Shipment ID

Must be unique and not null — violation → **reject**.

### Shipment Dates

Accepted formats: `MM/DD/YYYY`, `MM-DD-YYYY`. Any other date format → **reject**.

## 8. Clean and Load Pipeline — Requirements

- Apply carrier, status, freight cost, shipment ID, and date rules above during load.
- Normalize accepted status values per the mapping table.
- Parse accepted date formats into a consistent internal date type.
- Every rejected row must be logged (row id + reason) — this log feeds `/status/dq-report`.
- Rejected rows are excluded from `shipments_clean`.

## 9. `shipments_clean` Schema (Staging Table)

| Field | Type |
|---|---|
| shipment_id | string, PK, unique, not null |
| carrier | string (DHL / BLUEDART / FEDEX) |
| ship_date | date |
| status | enum (Delayed / In Transit / Delivered / Pending / Accepted) |
| origin | string |
| destination | string |
| freight_cost | float, > 0 |
| expected_delivery_date | date |
| delivered_date | date |

## 10. API Contract (3 Required Endpoints — MVP Floor)

### `GET /status/summary`

Returns aggregate KPIs.

```json
{
  "total_shipments": 0,
  "in_transit": 0,
  "delivered": 0,
  "delayed": 0,
  "pending": 0,
  "on_time_pct": 0.0
}
```

### `GET /status/shipments`

Returns filterable shipment records. Query params: `status`, `carrier`, `origin`, `destination`

```json
[
  {
    "shipment_id": "SH00001",
    "carrier": "DHL",
    "status": "Delayed",
    "origin": "Pune",
    "destination": "Bangalore",
    "freight_cost": 89.12,
    "expected_delivery_date": "2024-01-27",
    "delivered_date": "2024-01-27"
  }
]
```

### `GET /status/dq-report`

Returns real PASS/FAIL, not a stub. If something is broken in the pipeline then it returns "Failure", else it returns "Pass".

```json
{
  "result": "PASS",
  "checks_run": ["carrier_valid", "status_valid", "freight_cost_positive",
                 "shipment_id_unique_not_null", "date_format_valid"],
  "failures": [
    {"shipment_id": "SH00004", "check": "date_format_valid",
     "reason": "04-06-2024 not in accepted formats"},
    {"shipment_id": "SH00011", "check": "date_format_valid",
     "reason": "not-a-date"}
  ]
}
```

## 10b. AI Assistant API — `POST /ai/chat`

A Claude-powered chatbot endpoint that answers natural-language questions about the live shipment project — data, carriers, routes, freight costs, data quality, and the API/architecture itself. Backed by `app/ai_service.py` and exposed via the `POST /ai/chat` route in `app/main.py`.

### Model & Configuration

- **Model:** `claude-sonnet-4-6` (Anthropic Messages API), `max_tokens = 1000`
- **API key:** loaded from `ANTHROPIC_API_KEY` in a project-root `.env` file (via python-dotenv)
- **Auth:** endpoint is protected — requires a valid OAuth2 Bearer token (same as other write-facing routes)

### System Prompt Scope

The assistant is scoped to the Shipment Operations Assistant persona. It is instructed to answer only questions about shipment data, carriers, status, routes, freight costs, delivery delays, data quality/rejected records, dashboard functionality, the FastAPI APIs, OAuth2 authentication, background refresh, and project architecture — using only the context supplied in the request, never inventing shipment data, and explicitly saying so when information isn't available in context. It declines unrelated general questions.

### Request

```
POST /ai/chat
Authorization: Bearer <token>
Content-Type: application/json

{
  "message": "Which carrier has the most delayed shipments?"
}
```

### Response

```json
{
  "answer": "Based on the current data, DHL has the most delayed shipments..."
}
```

### Context Injected Per Request

On every call, the endpoint assembles fresh context from the live pipeline and passes it to the model alongside the user's question:

- Current cleaned shipment records (from `shipments_clean`) and total count
- Current rejected-shipment count
- The live `/status/dq-report` result
- A summary of the project's own API surface (`/status/summary`, `/status/shipments`, `/status/dq-report`, `/ai/chat`)
- Notes on OAuth2 Bearer authentication and the 15-second background dashboard refresh

## 11. Dashboard Requirements (Swagger Acceptable as MVP UI)

- **KPI cards:** Total Shipments, In Transit, Delivered, Delayed
- **Shipment Status:** donut/pie chart
- **Carrier Performance:** on-time % by shipments
- **Route Analysis:** origin → destination
- **Freight Cost Analysis:** cost by carrier
- **Shipment Exception Table:** Shipment | Carrier | Route | Status | ETA | Delivered Date

## 12. Stack

FastAPI, uvicorn, pandas, pydantic, sqlite3 (or psycopg2)

## 13. Out of Scope (MVP Floor) / Stretch Goals

- OAuth2 auth on write endpoints
- Background task for async refresh
- Basic HTML frontend (instead of Swagger-only)
- AI-generated plain-English daily summary
