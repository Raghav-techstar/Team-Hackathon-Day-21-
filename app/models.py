from pydantic import BaseModel
from typing import Optional


class SummaryResponse(BaseModel):
    total_shipments: int
    in_transit_shipments: int
    delivered_shipments: int
    delayed_shipments: int
    on_time_rate: float
    avg_freight_cost: float


class ShipmentResponse(BaseModel):
    shipment_id: str | None
    carrier: str | None
    ship_date: str | None
    status: Optional[str] | None
    origin: str | None
    destination: str | None
    freight_cost: Optional[float] | None
    expected_delivery_date: Optional[str] | None
    delivered_date: Optional[str] | None
    delay_days: Optional[float] | None


class DQCheck(BaseModel):
    check_name: str
    status: str
    details: str


class DQReportResponse(BaseModel):
    overall_status: str
    total_records: int
    duplicate_shipment_ids: int
    null_required_fields: int
    checks: list[DQCheck]

class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    answer: str