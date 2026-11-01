from typing import Dict, Type

from parking_lot.exceptions import InvalidInputError
from parking_lot.models.vehicle import Bike, Car, Truck, Vehicle


class VehicleFactory:
    """Factory pattern: callers pass a type string, never construct Car/Bike/Truck directly.

    Open/Closed: a new vehicle type is added with register(), without editing this class.
    """

    _registry: Dict[str, Type[Vehicle]] = {"BIKE": Bike, "CAR": Car, "TRUCK": Truck}

    @classmethod
    def register(cls, type_name: str, vehicle_cls: Type[Vehicle]) -> None:
        cls._registry[type_name.upper()] = vehicle_cls

    @classmethod
    def create(cls, type_name: str, plate: str) -> Vehicle:
        vehicle_cls = cls._registry.get((type_name or "").upper())
        if vehicle_cls is None:
            raise InvalidInputError(f"Unknown vehicle type '{type_name}'. Allowed: {sorted(cls._registry)}")
        return vehicle_cls(plate)
