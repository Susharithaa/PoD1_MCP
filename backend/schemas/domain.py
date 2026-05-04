from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ApiEnvelope(BaseModel):
    ok: bool = True
    data: Any
    error: str | None = None
    request_id: str | None = None


class TransportationCostIn(BaseModel):
    transport_type: str
    origin: str | None = None
    destination: str | None = None
    distance_km: float | None = None
    amount: float
    currency: str = "USD"
    receipt_url: str | None = None
    occurred_at: datetime | None = None


class TransportationCostOut(TransportationCostIn):
    id: str
    report_id: str


class ExpenseReportIn(BaseModel):
    employee_name: str
    report_number: str
    status: str = "DRAFT"
    currency: str = "USD"
    source_file_url: str | None = None
    transportation_costs: list[TransportationCostIn] = Field(default_factory=list)


class ExpenseReportOut(BaseModel):
    id: str
    employee_name: str
    report_number: str
    status: str
    currency: str
    total_amount: float
    source_file_url: str | None
    transportation_costs: list[TransportationCostOut] = Field(default_factory=list)
