"""Strategy pattern for pricing, Decorator pattern for add-on charges."""
import math
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict

from parking_lot.models.ticket import Ticket
from parking_lot.models.vehicle import VehicleType


class PricingStrategy(ABC):
    @abstractmethod
    def calculate(self, ticket: Ticket, exit_time: datetime) -> float: ...


class HourlyPricing(PricingStrategy):
    """Charges per started hour, minimum one hour."""

    DEFAULT_RATES = {VehicleType.BIKE: 10.0, VehicleType.CAR: 30.0, VehicleType.TRUCK: 60.0}

    def __init__(self, rates: Dict[VehicleType, float] = None):
        self._rates = rates or self.DEFAULT_RATES

    def calculate(self, ticket: Ticket, exit_time: datetime) -> float:
        seconds = max((exit_time - ticket.entry_time).total_seconds(), 0)
        hours = max(1, math.ceil(seconds / 3600))
        return hours * self._rates[ticket.vehicle_type]


class FlatPricing(PricingStrategy):
    """One fixed price per visit, e.g. for events."""

    DEFAULT_RATES = {VehicleType.BIKE: 20.0, VehicleType.CAR: 100.0, VehicleType.TRUCK: 200.0}

    def __init__(self, rates: Dict[VehicleType, float] = None):
        self._rates = rates or self.DEFAULT_RATES

    def calculate(self, ticket: Ticket, exit_time: datetime) -> float:
        return self._rates[ticket.vehicle_type]


class PricingDecorator(PricingStrategy, ABC):
    """Wraps another strategy and adds to its result. Decorators can be stacked."""

    def __init__(self, inner: PricingStrategy):
        self._inner = inner


class EVChargingCharge(PricingDecorator):
    def __init__(self, inner: PricingStrategy, charge: float = 50.0):
        super().__init__(inner)
        self._charge = charge

    def calculate(self, ticket: Ticket, exit_time: datetime) -> float:
        base = self._inner.calculate(ticket, exit_time)
        return base + self._charge if ticket.ev_charging else base


class GSTTax(PricingDecorator):
    def __init__(self, inner: PricingStrategy, rate: float = 0.18):
        super().__init__(inner)
        self._rate = rate

    def calculate(self, ticket: Ticket, exit_time: datetime) -> float:
        return round(self._inner.calculate(ticket, exit_time) * (1 + self._rate), 2)
