from abc import ABC, abstractmethod
from enum import Enum

from parking_lot.exceptions import InvalidInputError
from parking_lot.models.spot import SpotSize


class VehicleType(str, Enum):
    BIKE = "BIKE"
    CAR = "CAR"
    TRUCK = "TRUCK"


class Vehicle(ABC):
    """Abstract vehicle. Subclasses only declare their type and the spot size they need."""

    def __init__(self, plate: str):
        if not plate or not plate.strip():
            raise InvalidInputError("Number plate must not be empty")
        self._plate = plate.strip().upper()

    @property
    def plate(self) -> str:
        return self._plate

    @property
    @abstractmethod
    def vehicle_type(self) -> VehicleType: ...

    @property
    @abstractmethod
    def required_spot_size(self) -> SpotSize: ...


class Bike(Vehicle):
    vehicle_type = VehicleType.BIKE
    required_spot_size = SpotSize.SMALL


class Car(Vehicle):
    vehicle_type = VehicleType.CAR
    required_spot_size = SpotSize.MEDIUM


class Truck(Vehicle):
    vehicle_type = VehicleType.TRUCK
    required_spot_size = SpotSize.LARGE
