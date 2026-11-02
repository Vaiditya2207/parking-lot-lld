"""Observer pattern: the lot publishes spot changes; the display board and audit log react."""
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List

from parking_lot.models.spot import ParkingSpot

log = logging.getLogger("parking_lot.audit")


@dataclass(frozen=True)
class SpotEvent:
    spot_id: str
    floor_number: int
    size: str
    occupied: bool
    plate: str


class SpotObserver(ABC):
    @abstractmethod
    def on_spot_changed(self, event: SpotEvent) -> None: ...


class DisplayBoard(SpotObserver):
    """Keeps a live count of free spots per floor and size, like the board at the entrance."""

    def __init__(self):
        self._free: Dict[int, Dict[str, int]] = {}

    def load(self, spots: List[ParkingSpot]) -> None:
        self._free = {}
        for s in spots:
            counts = self._free.setdefault(s.floor_number, {})
            counts[s.size.name] = counts.get(s.size.name, 0) + (1 if s.is_free() else 0)

    def on_spot_changed(self, event: SpotEvent) -> None:
        counts = self._free.setdefault(event.floor_number, {})
        counts[event.size] = counts.get(event.size, 0) + (-1 if event.occupied else 1)

    def snapshot(self) -> Dict[int, Dict[str, int]]:
        return {floor: dict(counts) for floor, counts in sorted(self._free.items())}


class AuditLogger(SpotObserver):
    def on_spot_changed(self, event: SpotEvent) -> None:
        action = "PARKED" if event.occupied else "LEFT"
        log.info("%s %s spot=%s floor=%s", action, event.plate, event.spot_id, event.floor_number)
