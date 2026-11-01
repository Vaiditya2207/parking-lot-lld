from __future__ import annotations

from abc import ABC, abstractmethod
from enum import IntEnum
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from parking_lot.models.vehicle import Vehicle


class SpotSize(IntEnum):
    SMALL = 1
    MEDIUM = 2
    LARGE = 3


class ParkingSpot(ABC):
    """Abstract spot. A spot holds 0..1 vehicles; a vehicle fits if the spot is at least as big as it needs."""

    def __init__(self, spot_id: str, floor_number: int):
        self._spot_id = spot_id
        self._floor_number = floor_number
        self._vehicle: Optional[Vehicle] = None

    @property
    @abstractmethod
    def size(self) -> SpotSize: ...

    @property
    def spot_id(self) -> str:
        return self._spot_id

    @property
    def floor_number(self) -> int:
        return self._floor_number

    @property
    def vehicle(self) -> Optional[Vehicle]:
        return self._vehicle

    def is_free(self) -> bool:
        return self._vehicle is None

    def can_fit(self, vehicle: Vehicle) -> bool:
        return self.is_free() and self.size >= vehicle.required_spot_size

    def assign(self, vehicle: Vehicle) -> None:
        if not self.can_fit(vehicle):
            raise ValueError(f"Spot {self._spot_id} cannot take {vehicle.plate}")
        self._vehicle = vehicle

    def release(self) -> None:
        self._vehicle = None


class SmallSpot(ParkingSpot):
    size = SpotSize.SMALL


class MediumSpot(ParkingSpot):
    size = SpotSize.MEDIUM


class LargeSpot(ParkingSpot):
    size = SpotSize.LARGE
