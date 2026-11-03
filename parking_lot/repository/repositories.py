"""Repository layer. Services depend on the abstract classes (Dependency Inversion);
SQLite is just one implementation that could be swapped for Postgres or an in-memory fake."""
import sqlite3
import threading
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from parking_lot.models.spot import ParkingSpot
from parking_lot.models.ticket import Ticket, TicketStatus
from parking_lot.models.vehicle import VehicleType
from parking_lot.payments import PaymentReceipt

SCHEMA = """
CREATE TABLE IF NOT EXISTS floors (
    floor_number INTEGER PRIMARY KEY
);
CREATE TABLE IF NOT EXISTS spots (
    spot_id      TEXT PRIMARY KEY,
    floor_number INTEGER NOT NULL REFERENCES floors(floor_number),
    size         TEXT NOT NULL CHECK (size IN ('SMALL', 'MEDIUM', 'LARGE'))
);
CREATE TABLE IF NOT EXISTS tickets (
    ticket_id    TEXT PRIMARY KEY,
    plate        TEXT NOT NULL,
    vehicle_type TEXT NOT NULL CHECK (vehicle_type IN ('BIKE', 'CAR', 'TRUCK')),
    spot_id      TEXT NOT NULL REFERENCES spots(spot_id),
    entry_time   TEXT NOT NULL,
    exit_time    TEXT,
    ev_charging  INTEGER NOT NULL DEFAULT 0,
    fee          REAL,
    status       TEXT NOT NULL CHECK (status IN ('ACTIVE', 'PAID'))
);
CREATE TABLE IF NOT EXISTS payments (
    payment_id TEXT PRIMARY KEY,
    ticket_id  TEXT NOT NULL UNIQUE REFERENCES tickets(ticket_id),
    method     TEXT NOT NULL CHECK (method IN ('CASH', 'CARD', 'UPI')),
    amount     REAL NOT NULL CHECK (amount >= 0),
    reference  TEXT NOT NULL,
    paid_at    TEXT NOT NULL
);
-- Database-level guards: a spot or a vehicle can have at most one ACTIVE ticket.
CREATE UNIQUE INDEX IF NOT EXISTS ux_active_ticket_per_spot  ON tickets(spot_id) WHERE status = 'ACTIVE';
CREATE UNIQUE INDEX IF NOT EXISTS ux_active_ticket_per_plate ON tickets(plate)   WHERE status = 'ACTIVE';
CREATE INDEX IF NOT EXISTS ix_tickets_status ON tickets(status);
"""


class Database:
    def __init__(self, path: str = "parking.db"):
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(SCHEMA)
        self.lock = threading.Lock()

    @property
    def conn(self) -> sqlite3.Connection:
        return self._conn

    def save_layout(self, spots: List[ParkingSpot]) -> None:
        with self.lock, self._conn:
            for s in spots:
                self._conn.execute("INSERT OR IGNORE INTO floors VALUES (?)", (s.floor_number,))
                self._conn.execute("INSERT OR IGNORE INTO spots VALUES (?, ?, ?)",
                                   (s.spot_id, s.floor_number, s.size.name))


class TicketRepository(ABC):
    @abstractmethod
    def save(self, ticket: Ticket) -> None: ...

    @abstractmethod
    def update(self, ticket: Ticket) -> None: ...

    @abstractmethod
    def get(self, ticket_id: str) -> Optional[Ticket]: ...

    @abstractmethod
    def find_active_by_plate(self, plate: str) -> Optional[Ticket]: ...

    @abstractmethod
    def list_active(self) -> List[Ticket]: ...


class PaymentRepository(ABC):
    @abstractmethod
    def save(self, ticket_id: str, receipt: PaymentReceipt, paid_at: datetime) -> None: ...


class SqliteTicketRepository(TicketRepository):
    def __init__(self, db: Database):
        self._db = db

    def save(self, ticket):
        with self._db.lock, self._db.conn:
            self._db.conn.execute(
                "INSERT INTO tickets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (ticket.ticket_id, ticket.plate, ticket.vehicle_type.value, ticket.spot_id,
                 ticket.entry_time.isoformat(), None, int(ticket.ev_charging), None, ticket.status.value))

    def update(self, ticket):
        with self._db.lock, self._db.conn:
            self._db.conn.execute(
                "UPDATE tickets SET exit_time = ?, fee = ?, status = ? WHERE ticket_id = ?",
                (ticket.exit_time.isoformat() if ticket.exit_time else None, ticket.fee,
                 ticket.status.value, ticket.ticket_id))

    def get(self, ticket_id):
        return self._one("SELECT t.*, s.floor_number FROM tickets t JOIN spots s USING (spot_id) "
                         "WHERE t.ticket_id = ?", (ticket_id,))

    def find_active_by_plate(self, plate):
        return self._one("SELECT t.*, s.floor_number FROM tickets t JOIN spots s USING (spot_id) "
                         "WHERE t.plate = ? AND t.status = 'ACTIVE'", (plate,))

    def list_active(self):
        with self._db.lock:
            rows = self._db.conn.execute("SELECT t.*, s.floor_number FROM tickets t JOIN spots s "
                                         "USING (spot_id) WHERE t.status = 'ACTIVE'").fetchall()
        return [self._to_ticket(r) for r in rows]

    def _one(self, sql, params):
        with self._db.lock:
            row = self._db.conn.execute(sql, params).fetchone()
        return self._to_ticket(row) if row else None

    @staticmethod
    def _to_ticket(row) -> Ticket:
        return Ticket(
            ticket_id=row["ticket_id"], plate=row["plate"], vehicle_type=VehicleType(row["vehicle_type"]),
            spot_id=row["spot_id"], floor_number=row["floor_number"],
            entry_time=datetime.fromisoformat(row["entry_time"]), ev_charging=bool(row["ev_charging"]),
            status=TicketStatus(row["status"]),
            exit_time=datetime.fromisoformat(row["exit_time"]) if row["exit_time"] else None,
            fee=row["fee"])


class SqlitePaymentRepository(PaymentRepository):
    def __init__(self, db: Database):
        self._db = db

    def save(self, ticket_id, receipt, paid_at):
        with self._db.lock, self._db.conn:
            self._db.conn.execute(
                "INSERT INTO payments VALUES (?, ?, ?, ?, ?, ?)",
                (receipt.payment_id, ticket_id, receipt.method, receipt.amount, receipt.reference,
                 paid_at.isoformat()))
