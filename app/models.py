from pydantic import BaseModel
from typing import Optional


class SummaryResponse(BaseModel):
    total_shipments: int
    on_time_rate: float
    avg_freight_cost: float


class ShipmentResponse(BaseModel):
    shipment_id: str
    carrier: str
    ship_date: str
    status: Optional[str]
    origin: str
    destination: str
    freight_cost: Optional[float]
    expected_delivery_date: Optional[str]
    delivered_date: Optional[str]
    delay_days: Optional[float]


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