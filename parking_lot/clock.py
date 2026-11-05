from datetime import datetime, timedelta


class DemoClock:
    """Real time plus an offset that can be moved forward, so a demo can show fees for a
    2-hour stay without waiting 2 hours. The service only sees a callable returning datetime."""

    def __init__(self):
        self._offset = timedelta()

    def __call__(self) -> datetime:
        return datetime.now() + self._offset

    def advance(self, minutes: int) -> None:
        self._offset += timedelta(minutes=minutes)

    @property
    def offset_minutes(self) -> int:
        return int(self._offset.total_seconds() // 60)
