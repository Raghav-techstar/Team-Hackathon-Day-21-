# ADR-001: Shipment Operations Control Tower — Architecture

## Status
Accepted

## Date
2026-08-21

## Context

Ops managers currently track live shipment status, on-time delivery, and data
quality issues across three separate spreadsheets. The team needed a single
internal dashboard, built and demoed within a one-day hackathon window, that:

- Ingests raw shipment data and enforces data-quality rules before it is
  trusted anywhere downstream.
- Exposes that data through a small set of well-defined APIs.
- Supports a live judge walkthrough via interactive API docs, with a minimal
  working frontend as a stretch goal.
- Allows natural-language questions about the data without building a full
  BI tool.

This ADR records the architectural decisions made to satisfy those
constraints under hackathon time pressure, and the trade-offs accepted as a
result.

## Decision

### 1. Pipeline shape: CSV → clean/load step → staging table → API layer

We adopted a linear pipeline rather than a real-time streaming or
event-driven design:

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
   |                |                  |                |
   |                |                  |          (calls Anthropic
   |                |                  |           Claude API with
   |                |                  |           live data as
   |                |                  |           context)
   -----------------------------------------------------
        |
Swagger UI / demo (live judge walkthrough)
```

- `shipment_cleaning.py` reads `raw_shipments.csv`, applies validation and
  normalization rules, and writes `Clean_Shipments.csv` and
  `Rejected_Shipments.csv` to `data/`.
- `postgres_loader.py` separately loads the cleaned/rejected data into a
  PostgreSQL `shipments_clean` staging table for downstream/database use.
- The FastAPI layer (`app/data_loader.py`) reads directly from the CSV
  outputs rather than querying PostgreSQL live, keeping the API's read path
  simple and dependency-free during the demo.
- `/ai/chat` sits alongside the three read endpoints as a fourth consumer of
  `shipments_clean`: on each request it re-reads the same cleaned/rejected
  data and the live `/status/dq-report` result, folds them into a prompt,
  and forwards that to the Anthropic Claude API (`app/ai_service.py`) to
  answer natural-language questions. It is the only endpoint in the diagram
  that calls out to an external service rather than just serving local
  data.

**Rationed accepted:** the API layer is not reading from the database it
loads into. This was accepted to reduce moving parts under time pressure;
see Consequences.

### 2. Reject-at-load data quality enforcement

Data quality is enforced once, at load time, rather than validated on every
read:

- **Carrier:** only `DHL`, `BLUEDART`, `FEDEX` accepted; anything else is
  rejected.
- **Status:** raw values are mapped to a fixed normalized set (`Delayed`,
  `Delivered`, `In Transit`, `Pending`, `Accepted`); unmapped raw values are
  rejected.
- **Freight cost:** must be `> 0`, else rejected.
- **Shipment ID:** must be unique and not null, else rejected.
- **Ship date:** only `MM/DD/YYYY` and `MM-DD-YYYY` are accepted formats;
  anything else is rejected.

Every rejected row is logged with a row id and reason. This log is the
source of truth for `GET /status/dq-report`, which returns a real
`PASS`/`FAIL` result and the list of failing checks — not a stub.

**Rationale:** consumers of `shipments_clean` and the `/status/*` endpoints
never have to re-validate data; a single, auditable checkpoint owns
correctness.

### 3. Framework and stack: FastAPI + pandas + PostgreSQL

- **FastAPI** for the API layer — async-capable, automatic OpenAPI/Swagger
  docs generation (used directly as the MVP UI and demo surface), and
  built-in `pydantic` request/response validation.
- **pandas** for the cleaning/transform logic and for serving CSV-backed
  reads in the API layer.
- **PostgreSQL** (via SQLAlchemy + `psycopg`) as the staging store for the
  cleaned data, positioning the project to move off CSV files without
  changing the cleaning logic.
- **pydantic** models (`SummaryResponse`, `ShipmentResponse`,
  `DQReportResponse`, `ChatRequest`, `ChatResponse`) define and validate all
  API contracts.

### 4. Authentication: OAuth2 password flow with a static demo user

All `/status/*` and `/ai/chat` endpoints require a bearer token, obtained
via `POST /token` using `OAuth2PasswordRequestForm`. Credentials
(`admin` / `admin123`) are hardcoded in `app/auth.py`, and the returned
token is simply the username, verified with a direct string comparison in
`get_current_user`.

**Rationale:** demonstrates the shape of a secured API (Swagger UI's
"Authorize" flow works end-to-end) without the cost of standing up a real
user store or JWT signing infrastructure for a one-day build. Explicitly
flagged as out-of-scope-for-production in the requirements doc.

### 5. AI Assistant: Claude-powered `/ai/chat` endpoint with per-request context injection

`POST /ai/chat` (`app/ai_service.py`) answers natural-language questions
about the project using the Anthropic Messages API (`claude-sonnet-4-6`,
`max_tokens=1000`), rather than a retrieval pipeline or vector store.

- On every request, the endpoint assembles fresh context: the current
  cleaned shipment records and count, rejected-shipment count, the live
  `/status/dq-report` result, a summary of the project's own API surface,
  and notes on auth and refresh behavior.
- A fixed system prompt scopes the assistant strictly to shipment data,
  carriers, routes, freight costs, delays, data quality, dashboard
  functionality, and the project's own architecture/APIs — instructing it
  not to invent data and to say when information isn't available in
  context, and to decline unrelated questions.
- The Anthropic API key is loaded from a project-root `.env` file
  (`ANTHROPIC_API_KEY`, via `python-dotenv`); the app raises at import time
  if it's missing.

**Rationale:** for the dataset sizes involved in the hackathon, stuffing
live context directly into the prompt is simpler and more accurate than
building retrieval, and keeps the assistant's answers grounded in the
current state of the data on every call.

### 6. Frontend: static files mounted on the FastAPI app itself

Rather than a separate frontend service/build pipeline, `frontend/`
(`index.html`, `app.js`, `style.css`) is mounted directly onto the FastAPI
app root via `StaticFiles(directory=FRONTEND_DIR, html=True)`. One process,
one port, one `uvicorn` command serves both the API and the dashboard UI.

**Rationale:** Swagger UI was accepted as the MVP floor for the UI per the
requirements doc; the static HTML/JS frontend was a stretch goal, and
mounting it on the same app avoided any additional deployment complexity.

## Consequences

**Positive**

- Single command (`uvicorn app.main:app --reload`) runs the entire system —
  API, docs, AI assistant, and dashboard UI.
- Data quality is enforced exactly once and is fully auditable via
  `/status/dq-report`.
- Swagger UI alone is sufficient for a live judge walkthrough; no separate
  frontend deployment was required to hit the MVP floor.
- The AI assistant's answers are always grounded in the current data state,
  with no separate indexing/retrieval step to keep in sync.

**Negative / accepted trade-offs**

- The API layer reads from CSV files (`Clean_Shipments.csv`,
  `Rejected_Shipments.csv`), not from the PostgreSQL `shipments_clean`
  table that `postgres_loader.py` populates. The database load and the API
  read path are not yet the same source of truth — acceptable for a
  same-day demo, but a real gap for production use.
- Authentication is a single hardcoded demo user with no password hashing,
  token expiry, or refresh flow. OAuth2 auth on write endpoints beyond this
  demo is explicitly listed as a stretch goal, not delivered.
- No background/async refresh job exists yet; the frontend re-polls on a
  fixed interval (15 seconds) rather than receiving pushed updates.
- Every `/ai/chat` call re-serializes the full cleaned/rejected dataset into
  the prompt context. This is fine at hackathon data volumes but will not
  scale to large shipment datasets without a retrieval or summarization
  step.

## Follow-ups (Out of Scope for MVP)

- Point the API read path at the PostgreSQL staging table instead of CSVs,
  so the load pipeline and the API share one source of truth.
- Replace the static demo credentials with real user management and
  OAuth2 auth on write endpoints.
- Add a background task for async data refresh instead of static CSV reads
  on each request.
- Build out the basic HTML frontend further, beyond the Swagger-only MVP
  floor.
- Add an AI-generated plain-English daily summary on top of the existing
  `/ai/chat` assistant.
