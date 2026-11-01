from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from parking_lot.exceptions import InvalidInputError, TicketAlreadyClosedError
from parking_lot.models.vehicle import VehicleType


class TicketStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PAID = "PAID"


class Ticket:
    """Created only through TicketBuilder."""

    def __init__(self, ticket_id: str, plate: str, vehicle_type: VehicleType, spot_id: str,
                 floor_number: int, entry_time: datetime, ev_charging: bool,
                 status: TicketStatus = TicketStatus.ACTIVE,
                 exit_time: Optional[datetime] = None, fee: Optional[float] = None):
        self.ticket_id = ticket_id
        self.plate = plate
        self.vehicle_type = vehicle_type
        self.spot_id = spot_id
        self.floor_number = floor_number
        self.entry_time = entry_time
        self.ev_charging = ev_charging
        self.status = status
        self.exit_time = exit_time
        self.fee = fee

    def close(self, exit_time: datetime, fee: float) -> None:
        if self.status != TicketStatus.ACTIVE:
            raise TicketAlreadyClosedError(f"Ticket {self.ticket_id} is already paid")
        self.exit_time = exit_time
        self.fee = fee
        self.status = TicketStatus.PAID


class TicketBuilder:
    """Builder pattern: a ticket has several required and optional fields; build() validates them once."""

    def __init__(self):
        self._plate = None
        self._vehicle_type = None
        self._spot_id = None
        self._floor_number = None
        self._entry_time = None
        self._ev_charging = False

    def for_vehicle(self, plate: str, vehicle_type: VehicleType) -> "TicketBuilder":
        self._plate, self._vehicle_type = plate, vehicle_type
        return self

    def at_spot(self, spot_id: str, floor_number: int) -> "TicketBuilder":
        self._spot_id, self._floor_number = spot_id, floor_number
        return self

    def entered_at(self, entry_time: datetime) -> "TicketBuilder":
        self._entry_time = entry_time
        return self

    def with_ev_charging(self, enabled: bool = True) -> "TicketBuilder":
        self._ev_charging = enabled
        return self

    def build(self) -> Ticket:
        missing = [name for name, value in [("vehicle", self._plate), ("spot", self._spot_id),
                                            ("entry_time", self._entry_time)] if value is None]
        if missing:
            raise InvalidInputError(f"Ticket is missing: {', '.join(missing)}")
        return Ticket(str(uuid.uuid4()), self._plate, self._vehicle_type, self._spot_id,
                      self._floor_number, self._entry_time, self._ev_charging)
