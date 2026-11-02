import threading
from typing import List, Optional

from parking_lot.exceptions import LotFullError
from parking_lot.models.floor import Floor
from parking_lot.models.spot import ParkingSpot
from parking_lot.models.vehicle import Vehicle
from parking_lot.patterns.allocation import NearestFirstAllocation, SpotAllocationStrategy
from parking_lot.patterns.observer import SpotEvent, SpotObserver


class ParkingLot:
    """Singleton: there is one physical lot, so every service shares one instance.

    The lot owns its floors (composition) and is the Observer subject for spot changes.
    It holds the lock that stops two cars from being given the same spot.
    """

    _instance: Optional["ParkingLot"] = None
    _instance_lock = threading.Lock()

    def __init__(self):
        raise RuntimeError("Use ParkingLot.instance()")

    @classmethod
    def instance(cls) -> "ParkingLot":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:  # double-checked locking
                    lot = object.__new__(cls)
                    lot._setup()
                    cls._instance = lot
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Only for tests and app restarts."""
        with cls._instance_lock:
            cls._instance = None

    def _setup(self) -> None:
        self._floors: List[Floor] = []
        self._observers: List[SpotObserver] = []
        self._allocation: SpotAllocationStrategy = NearestFirstAllocation()
        self.lock = threading.RLock()

    # configuration
    def add_floor(self, floor: Floor) -> None:
        self._floors.append(floor)

    def set_allocation_strategy(self, strategy: SpotAllocationStrategy) -> None:
        self._allocation = strategy

    def subscribe(self, observer: SpotObserver) -> None:
        self._observers.append(observer)

    # queries
    @property
    def floors(self) -> List[Floor]:
        return list(self._floors)

    def all_spots(self) -> List[ParkingSpot]:
        return [s for f in self._floors for s in f.spots]

    def find_spot(self, spot_id: str) -> Optional[ParkingSpot]:
        return next((s for s in self.all_spots() if s.spot_id == spot_id), None)

    # commands (callers must hold self.lock)
    def park(self, vehicle: Vehicle) -> ParkingSpot:
        spot = self._allocation.find_spot(self._floors, vehicle)
        if spot is None:
            raise LotFullError(f"No free spot for a {vehicle.vehicle_type.value}")
        spot.assign(vehicle)
        self._notify(spot, occupied=True, plate=vehicle.plate)
        return spot

    def occupy(self, spot_id: str, vehicle: Vehicle) -> None:
        """Re-occupy a known spot, used when restoring active tickets after a restart."""
        spot = self.find_spot(spot_id)
        if spot is not None and spot.is_free():
            spot.assign(vehicle)

    def release(self, spot_id: str) -> None:
        spot = self.find_spot(spot_id)
        if spot is None or spot.is_free():
            return
        plate = spot.vehicle.plate
        spot.release()
        self._notify(spot, occupied=False, plate=plate)

    def _notify(self, spot: ParkingSpot, occupied: bool, plate: str) -> None:
        event = SpotEvent(spot.spot_id, spot.floor_number, spot.size.name, occupied, plate)
        for observer in self._observers:
            observer.on_spot_changed(event)
