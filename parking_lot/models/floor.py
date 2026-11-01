from typing import List

from parking_lot.models.spot import ParkingSpot


class Floor:
    """A floor owns its spots (composition): spots are created with the floor and never move."""

    def __init__(self, number: int, spots: List[ParkingSpot]):
        self._number = number
        self._spots = list(spots)

    @property
    def number(self) -> int:
        return self._number

    @property
    def spots(self) -> List[ParkingSpot]:
        return list(self._spots)

    def free_spots(self) -> List[ParkingSpot]:
        return [s for s in self._spots if s.is_free()]
