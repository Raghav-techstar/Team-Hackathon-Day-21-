# Shipment Operations Control Tower — Requirements

## 1. Overview
Internal dashboard for ops managers to view live shipment status, on-time delivery, and data quality issues from one place instead of three spreadsheets.

## 2. Architecture (locked)

```
raw_shipments.csv
      |
Clean and load pipeline (profile, standardize, log)
      |
shipments_clean (staging table)
      |
  ------------------------------------
  |              |                   |
/status/summary /status/shipments /status/dq-report
  ------------------------------------
      |
Swagger UI / demo (live judge walkthrough)
```

## 3. Raw Data Schema — `raw_shipments.csv`

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

## 4. Data Quality Rules (reject/accept logic)

**Carrier**
- Accept only: `DHL`, `BLUEDART`, `FEDEX`
- Any other carrier value → **reject**

**Status** (raw → normalized)
| Raw value | Normalized value |
|---|---|
| Delayed | Delayed |
| DELIVERED | Delivered |
| In Transit | In Transit |
| IN_TRANSIT | In Transit |
| in-transit | In Transit |
| pending | Pending |
| *(blank)* | Accepted |

- Any raw status value not in the table above → **reject**

**Freight Cost**
- `freight_cost <= 0` → **reject**

**Shipment ID**
- Must be unique and not null → violation → **reject**

**Shipment Dates**
- Accepted formats: `MM/DD/YYYY`, `MM-DD-YYYY`
- Any other date format → **reject**

## 5. Clean and Load Pipeline — Requirements

- Apply carrier, status, freight cost, shipment ID, and date rules above during load.
- Normalize accepted status values per the mapping table.
- Parse accepted date formats into a consistent internal date type.
- Every rejected row must be logged (row id + reason) — this log feeds `/status/dq-report`.
- Rejected rows are excluded from `shipments_clean`.

## 6. `shipments_clean` Schema (staging table)

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

## 7. API Contract (3 required endpoints — MVP floor)

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
Returns filterable shipment records.
Query params: `status`, `carrier`, `origin`, `destination`
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
Returns real PASS/FAIL, not a stub.
If something is broken in the pipeline then it returns "Failure" else it returns "Pass".


```json
{
  "result": "PASS",
  "checks_run": ["carrier_valid", "status_valid", "freight_cost_positive", "shipment_id_unique_not_null", "date_format_valid"],
  "failures": [
    {"shipment_id": "SH00004", "check": "date_format_valid", "reason": "04-06-2024 not in accepted formats"},
    {"shipment_id": "SH00011", "check": "date_format_valid", "reason": "not-a-date"}
  ]
}
```

## 8. Dashboard Requirements (from mockup — Swagger acceptable as MVP UI)

- **KPI cards:** Total Shipments, In Transit, Delivered, Delayed
- **Shipment Status:** donut/pie chart
- **Carrier Performance:** on-time % by shipments
- **Route Analysis:** origin → destination
- **Freight Cost Analysis:** cost by carrier
- **Shipment Exception Table:** Shipment | Carrier | Route | Status | ETA | Delivered Date

## 9. Stack

FastAPI, uvicorn, pandas, pydantic, sqlite3 (or psycopg2)

## 10. Out of Scope (MVP floor) / Stretch Goals

- OAuth2 auth on write endpoints
- Background task for async refresh
- Basic HTML frontend (instead of Swagger-only)
- AI-generated plain-English daily summary
