"""Controller layer: HTTP in, HTTP out. No business rules here, only translation to and from the service."""
from fastapi import APIRouter, Request

from parking_lot.api.schemas import (AvailabilityResponse, EntryRequest, ErrorResponse, ExitRequest,
                                     ExitResponse, QuoteResponse, TicketResponse)
from parking_lot.models.ticket import Ticket
from parking_lot.payments import create_payment
from parking_lot.service.parking_service import ParkingService

router = APIRouter()
ERRORS = {code: {"model": ErrorResponse} for code in (400, 402, 404, 409)}


def _service(request: Request) -> ParkingService:
    return request.app.state.service


def _to_response(t: Ticket) -> TicketResponse:
    return TicketResponse(ticket_id=t.ticket_id, plate=t.plate, vehicle_type=t.vehicle_type.value,
                          spot_id=t.spot_id, floor_number=t.floor_number, entry_time=t.entry_time,
                          ev_charging=t.ev_charging, status=t.status.value, exit_time=t.exit_time, fee=t.fee)


@router.post("/entry", response_model=TicketResponse, status_code=201, responses=ERRORS)
def entry(body: EntryRequest, request: Request):
    ticket = _service(request).park(body.vehicle_type, body.plate, body.ev_charging)
    return _to_response(ticket)


@router.get("/tickets/{ticket_id}/quote", response_model=QuoteResponse, responses=ERRORS)
def quote(ticket_id: str, request: Request):
    return QuoteResponse(ticket_id=ticket_id, amount_due=_service(request).quote(ticket_id))


@router.post("/exit/{ticket_id}", response_model=ExitResponse, responses=ERRORS)
def exit_lot(ticket_id: str, body: ExitRequest, request: Request):
    payment = create_payment(body.payment_method, body.card_number, body.upi_id)
    result = _service(request).exit(ticket_id, payment)
    return ExitResponse(ticket=_to_response(result.ticket), payment_id=result.receipt.payment_id,
                        amount_paid=result.receipt.amount, payment_reference=result.receipt.reference)


@router.get("/availability", response_model=AvailabilityResponse)
def availability(request: Request):
    return AvailabilityResponse(free_spots=_service(request).availability())
