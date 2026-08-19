from pathlib import Path

import pandas as pd

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles

from app.data_loader import (
    load_clean_shipments,
    load_rejected_shipments,
)

from app.dq_checks import data_quality_report

from app.models import (
    SummaryResponse,
    ShipmentResponse,
    DQReportResponse,
)


app = FastAPI(
    title="Operational Status Dashboard",
    description=(
        "FastAPI service for the Day 21 "
        "Operational Status Dashboard."
    ),
    version="1.0.0",
)


# ============================================================
# FRONTEND
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"


# ============================================================
# GET /status/summary
# ============================================================

@app.get(
    "/status/summary",
    response_model=SummaryResponse,
    tags=["Status"],
)
def get_summary():
    """Return top-level shipment KPIs."""

    try:
        clean_df = load_clean_shipments()

    except FileNotFoundError as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        )

    total_shipments = len(clean_df)

    if total_shipments == 0:
        return {
            "total_shipments": 0,
            "on_time_rate": 0.0,
            "avg_freight_cost": 0.0,
        }

    on_time_shipments = int(
        (clean_df["delay_days"].fillna(0) <= 0).sum()
    )

    on_time_rate = round(
        (on_time_shipments / total_shipments) * 100,
        2,
    )

    avg_freight_cost = round(
        clean_df["freight_cost"]
        .dropna()
        .astype(float)
        .mean(),
        2,
    )

    return {
        "total_shipments": total_shipments,
        "on_time_rate": on_time_rate,
        "avg_freight_cost": avg_freight_cost,
    }


# ============================================================
# GET /status/shipments
# ============================================================

@app.get(
    "/status/shipments",
    response_model=list[ShipmentResponse],
    tags=["Status"],
)
def get_shipments(
    carrier: str | None = Query(
        default=None,
        description="Filter by carrier",
    ),
    status: str | None = Query(
        default=None,
        description="Filter by shipment status",
    ),
):
    """Return cleaned shipment records."""

    try:
        clean_df = load_clean_shipments()

    except FileNotFoundError as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        )

    if carrier:
        clean_df = clean_df[
            clean_df["carrier"]
            .astype(str)
            .str.upper()
            == carrier.upper()
        ]

    if status:
        clean_df = clean_df[
            clean_df["status"]
            .fillna("")
            .astype(str)
            .str.lower()
            == status.lower()
        ]

    records = []

    for record in clean_df.to_dict(orient="records"):

        status_value = record.get("status")

        if pd.isna(status_value):
            status_value = None
        else:
            status_value = str(status_value)

        freight_cost = record.get("freight_cost")

        if pd.isna(freight_cost):
            freight_cost = None
        else:
            freight_cost = float(freight_cost)

        delay_days = record.get("delay_days")

        if pd.isna(delay_days):
            delay_days = None
        else:
            delay_days = float(delay_days)

        expected_date = record.get(
            "Expected Delivery Date"
        )

        if pd.isna(expected_date):
            expected_date = None
        else:
            expected_date = str(expected_date)

        delivered_date = record.get(
            "Delivered Date"
        )

        if pd.isna(delivered_date):
            delivered_date = None
        else:
            delivered_date = str(delivered_date)

        records.append(
            {
                "shipment_id": str(
                    record["shipment_id"]
                ),
                "carrier": str(
                    record["carrier"]
                ),
                "ship_date": str(
                    record["ship_date"]
                ),
                "status": status_value,
                "origin": str(
                    record["origin"]
                ),
                "destination": str(
                    record["destination"]
                ),
                "freight_cost": freight_cost,
                "expected_delivery_date": expected_date,
                "delivered_date": delivered_date,
                "delay_days": delay_days,
            }
        )

    return records


# ============================================================
# GET /status/dq-report
# ============================================================

@app.get(
    "/status/dq-report",
    response_model=DQReportResponse,
    tags=["Data Quality"],
)
def get_dq_report():
    """Return computed data-quality results."""

    try:
        clean_df = load_clean_shipments()
        rejected_df = load_rejected_shipments()

    except FileNotFoundError as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        )

    return data_quality_report(
        clean_df,
        rejected_df,
    )


# ============================================================
# SERVE FRONTEND
# ============================================================

app.mount(
    "/",
    StaticFiles(
        directory=FRONTEND_DIR,
        html=True,
    ),
    name="frontend",
)