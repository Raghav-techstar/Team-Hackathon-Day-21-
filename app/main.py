from fastapi.security import OAuth2PasswordRequestForm
from fastapi import (
    FastAPI,
    HTTPException,
    Query,
    Depends,
)

from app.auth import (
    USERNAME,
    PASSWORD,
    get_current_user,
)

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


from app.ai_service import ask_ai

from app.models import (
    SummaryResponse,
    ShipmentResponse,
    DQReportResponse,
    ChatRequest,
    ChatResponse,
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
# POST /token
# ============================================================

@app.post(
    "/token",
    tags=["Authentication"],
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    """Return an OAuth2 bearer token."""

    if (
        form_data.username != USERNAME
        or form_data.password != PASSWORD
    ):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    return {
        "access_token": form_data.username,
        "token_type": "bearer",
    }


# ============================================================
# GET /status/summary
# ============================================================

@app.get(
    "/status/summary",
    response_model=SummaryResponse,
    tags=["Status"],
)
def get_summary(current_user: str = Depends(get_current_user),):
    """Return top-level shipment KPIs."""

    try:
        clean_df = load_clean_shipments()

    except FileNotFoundError as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        )

    total_shipments = len(clean_df)

    normalized_status = (
        clean_df["status"]
        .fillna("")
        .astype(str)
        .str.lower()
        .str.replace("_", " ", regex=False)
        .str.replace("-", " ", regex=False)
    )

    in_transit_shipments = int(
        (normalized_status == "in transit").sum()
    )
    delivered_shipments = int(
        (normalized_status == "delivered").sum()
    )
    delayed_shipments = int(
        (normalized_status == "delayed").sum()
    )

    if total_shipments == 0:
        return {
            "total_shipments": 0,
            "in_transit_shipments": 0,
            "delivered_shipments": 0,
            "delayed_shipments": 0,
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
        "in_transit_shipments": in_transit_shipments,
        "delivered_shipments": delivered_shipments,
        "delayed_shipments": delayed_shipments,
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
    current_user: str = Depends(get_current_user),

    carrier: str | None = Query(
        default=None,
        description="Filter by carrier",
    ),

    status: str | None = Query(
        default=None,
        description="Filter by shipment status",
    ),

    limit: int = Query(
        default=50,
        ge=1,
        le=100,
        description="Maximum number of records to return",
    ),

    offset: int = Query(
        default=0,
        ge=0,
        description="Number of records to skip",
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

    clean_df = clean_df.iloc[offset:offset + limit]

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
            "Delivered_Date"
        )

        if pd.isna(delivered_date):
            delivered_date = None
        else:
            delivered_date = str(delivered_date)

        records.append(
            {
                "shipment_id": (
                    None
                    if pd.isna(record.get("shipment_id"))
                    else str(record.get("shipment_id"))
                ),

                "carrier": (
                    None
                    if pd.isna(record.get("carrier"))
                    else str(record.get("carrier"))
                ),

                "ship_date": (
                    None
                    if pd.isna(record.get("ship_date"))
                    else str(record.get("ship_date"))
                ),

                "status": status_value,
                "origin": (
                    None
                    if pd.isna(record.get("origin"))
                    else str(record.get("origin"))
                ),

                "destination": (
                    None
                    if pd.isna(record.get("destination"))
                    else str(record.get("destination"))
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
def get_dq_report(current_user: str = Depends(get_current_user),):
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
# POST /ai/chat
# ============================================================

@app.post(
    "/ai/chat",
    response_model=ChatResponse,
    tags=["AI Assistant"],
)
def ai_chat(
    request: ChatRequest,
    current_user: str = Depends(get_current_user),
):
    """Answer questions about the shipment project."""

    try:

        clean_df = load_clean_shipments()
        rejected_df = load_rejected_shipments()

        dq_report = data_quality_report(
            clean_df,
            rejected_df,
        )

        context = f"""
CURRENT SHIPMENT DATA
---------------------

Total shipments:
{len(clean_df)}

Shipment records:
{clean_df.to_dict(orient="records")}


REJECTED SHIPMENT DATA
----------------------

Rejected records:
{len(rejected_df)}


DATA QUALITY REPORT
-------------------

{dq_report}


PROJECT APIs
------------

GET /status/summary
Returns shipment KPIs.

GET /status/shipments
Returns shipment records and supports
carrier and status filtering.

GET /status/dq-report
Returns the current data-quality result.

POST /ai/chat
Answers questions about this project
and its current shipment data.


AUTHENTICATION
--------------

The APIs use OAuth2 Bearer authentication.


BACKGROUND REFRESH
-------------------

The frontend refreshes dashboard data
every 15 seconds without reloading
the page.
"""

        answer = ask_ai(
            request.message,
            context,
        )

        return {
            "answer": answer
        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error),
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