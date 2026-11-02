"""Strategy pattern for choosing which free spot a vehicle gets."""
from abc import ABC, abstractmethod
from typing import List, Optional

from parking_lot.models.floor import Floor
from parking_lot.models.spot import ParkingSpot
from parking_lot.models.vehicle import Vehicle


class SpotAllocationStrategy(ABC):
    @abstractmethod
    def find_spot(self, floors: List[Floor], vehicle: Vehicle) -> Optional[ParkingSpot]: ...


class NearestFirstAllocation(SpotAllocationStrategy):
    """Lowest floor first, then first spot on that floor that fits."""

    def find_spot(self, floors, vehicle):
        for floor in sorted(floors, key=lambda f: f.number):
            for spot in floor.spots:
                if spot.can_fit(vehicle):
                    return spot
        return None


class BestFitAllocation(SpotAllocationStrategy):
    """Smallest spot that fits, so a bike does not take a truck spot while small spots are free."""

    def find_spot(self, floors, vehicle):
        candidates = [s for f in floors for s in f.spots if s.can_fit(vehicle)]
        return min(candidates, key=lambda s: (s.size, s.floor_number), default=None)
