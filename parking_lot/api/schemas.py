from datetime import datetime
from typing import Dict, Literal, Optional

from pydantic import BaseModel, Field


class EntryRequest(BaseModel):
    vehicle_type: Literal["BIKE", "CAR", "TRUCK"]
    plate: str = Field(min_length=1, max_length=15, examples=["DL01AB1234"])
    ev_charging: bool = False


class TicketResponse(BaseModel):
    ticket_id: str
    plate: str
    vehicle_type: str
    spot_id: str
    floor_number: int
    entry_time: datetime
    ev_charging: bool
    status: str
    exit_time: Optional[datetime] = None
    fee: Optional[float] = None


class ExitRequest(BaseModel):
    payment_method: Literal["CASH", "CARD", "UPI"]
    card_number: Optional[str] = Field(default=None, examples=["4111111111111111"])
    upi_id: Optional[str] = Field(default=None, examples=["yashi@okaxis"])


class ExitResponse(BaseModel):
    ticket: TicketResponse
    payment_id: str
    amount_paid: float
    payment_reference: str


class QuoteResponse(BaseModel):
    ticket_id: str
    amount_due: float


class SpotResponse(BaseModel):
    spot_id: str
    floor_number: int
    size: str
    occupied: bool
    ticket: Optional[TicketResponse] = None


class AdvanceClockRequest(BaseModel):
    minutes: int = Field(gt=0, le=24 * 60, examples=[60])


class ClockResponse(BaseModel):
    now: datetime
    offset_minutes: int


class AvailabilityResponse(BaseModel):
    free_spots: Dict[int, Dict[str, int]]


class ErrorResponse(BaseModel):
    error: str
    message: str
