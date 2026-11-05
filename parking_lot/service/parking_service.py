from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Dict, List, Optional

from parking_lot.core.parking_lot import ParkingLot
from parking_lot.exceptions import TicketAlreadyClosedError, TicketNotFoundError, VehicleAlreadyParkedError
from parking_lot.models.ticket import Ticket, TicketBuilder, TicketStatus
from parking_lot.models.vehicle import Vehicle
from parking_lot.patterns.observer import DisplayBoard
from parking_lot.patterns.pricing import PricingStrategy
from parking_lot.patterns.vehicle_factory import VehicleFactory
from parking_lot.payments import PaymentMethod, PaymentReceipt
from parking_lot.repository.repositories import PaymentRepository, TicketRepository


@dataclass
class ExitResult:
    ticket: Ticket
    receipt: PaymentReceipt


@dataclass
class SpotView:
    spot_id: str
    floor_number: int
    size: str
    ticket: Optional[Ticket]


class ParkingService:
    """Business rules for entry and exit. Depends only on abstractions passed in (Dependency Inversion)."""

    def __init__(self, lot: ParkingLot, tickets: TicketRepository, payments: PaymentRepository,
                 pricing: PricingStrategy, board: DisplayBoard,
                 clock: Callable[[], datetime] = datetime.now):
        self._lot = lot
        self._tickets = tickets
        self._payments = payments
        self._pricing = pricing
        self._board = board
        self._clock = clock

    def restore_active_tickets(self) -> None:
        """After a restart, mark spots of still-active tickets as occupied again."""
        with self._lot.lock:
            for t in self._tickets.list_active():
                self._lot.occupy(t.spot_id, VehicleFactory.create(t.vehicle_type.value, t.plate))
            self._board.load(self._lot.all_spots())

    def park(self, vehicle_type: str, plate: str, ev_charging: bool = False) -> Ticket:
        vehicle: Vehicle = VehicleFactory.create(vehicle_type, plate)
        # One lock around check + allocate + save: two requests can never get the same spot
        # and the same car cannot be parked twice.
        with self._lot.lock:
            if self._tickets.find_active_by_plate(vehicle.plate):
                raise VehicleAlreadyParkedError(f"{vehicle.plate} is already parked")
            spot = self._lot.park(vehicle)
            ticket = (TicketBuilder()
                      .for_vehicle(vehicle.plate, vehicle.vehicle_type)
                      .at_spot(spot.spot_id, spot.floor_number)
                      .entered_at(self._clock())
                      .with_ev_charging(ev_charging)
                      .build())
            try:
                self._tickets.save(ticket)
            except Exception:
                self._lot.release(spot.spot_id)  # roll back the in-memory allocation
                raise
            return ticket

    def quote(self, ticket_id: str) -> float:
        ticket = self._get_active(ticket_id)
        return self._pricing.calculate(ticket, self._clock())

    def exit(self, ticket_id: str, payment: PaymentMethod) -> ExitResult:
        with self._lot.lock:
            ticket = self._get_active(ticket_id)
            now = self._clock()
            fee = self._pricing.calculate(ticket, now)
            receipt = payment.pay(fee)  # raises PaymentFailedError; ticket stays ACTIVE, spot stays taken
            ticket.close(now, fee)
            self._tickets.update(ticket)
            self._payments.save(ticket.ticket_id, receipt, now)
            self._lot.release(ticket.spot_id)
            return ExitResult(ticket, receipt)

    def availability(self) -> Dict[int, Dict[str, int]]:
        return self._board.snapshot()

    def spots(self) -> List[SpotView]:
        """Every spot with the ticket parked in it, for the floor map."""
        with self._lot.lock:
            active = {t.spot_id: t for t in self._tickets.list_active()}
            return [SpotView(s.spot_id, s.floor_number, s.size.name, active.get(s.spot_id))
                    for s in self._lot.all_spots()]

    def _get_active(self, ticket_id: str) -> Ticket:
        ticket = self._tickets.get(ticket_id)
        if ticket is None:
            raise TicketNotFoundError(f"Ticket {ticket_id} not found")
        if ticket.status != TicketStatus.ACTIVE:
            raise TicketAlreadyClosedError(f"Ticket {ticket_id} is already paid")
        return ticket
