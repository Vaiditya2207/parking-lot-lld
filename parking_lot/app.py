"""Composition root: the only place that picks concrete classes and wires them together."""
import logging
from datetime import datetime
from typing import Callable, Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from parking_lot.api.controller import router
from parking_lot.core.parking_lot import ParkingLot
from parking_lot.exceptions import ParkingError
from parking_lot.models.floor import Floor
from parking_lot.models.spot import LargeSpot, MediumSpot, SmallSpot
from parking_lot.patterns.observer import AuditLogger, DisplayBoard
from parking_lot.patterns.pricing import EVChargingCharge, GSTTax, HourlyPricing, PricingStrategy
from parking_lot.repository.repositories import Database, SqlitePaymentRepository, SqliteTicketRepository
from parking_lot.service.parking_service import ParkingService


def default_floors():
    """2 floors, each with 2 small, 3 medium and 1 large spot."""
    floors = []
    for n in (1, 2):
        spots = ([SmallSpot(f"F{n}-S{i}", n) for i in (1, 2)]
                 + [MediumSpot(f"F{n}-M{i}", n) for i in (1, 2, 3)]
                 + [LargeSpot(f"F{n}-L1", n)])
        floors.append(Floor(n, spots))
    return floors


def build_service(db_path: str = "parking.db", floors=None, pricing: Optional[PricingStrategy] = None,
                  clock: Callable[[], datetime] = datetime.now) -> ParkingService:
    ParkingLot.reset()
    lot = ParkingLot.instance()
    for floor in floors if floors is not None else default_floors():
        lot.add_floor(floor)

    board = DisplayBoard()
    lot.subscribe(board)
    lot.subscribe(AuditLogger())

    db = Database(db_path)
    db.save_layout(lot.all_spots())

    # Strategy wrapped by two decorators: hourly rate, + EV charge if used, then + 18% GST.
    pricing = pricing or GSTTax(EVChargingCharge(HourlyPricing()))
    service = ParkingService(lot, SqliteTicketRepository(db), SqlitePaymentRepository(db), pricing, board, clock)
    service.restore_active_tickets()
    return service


def create_app(service: Optional[ParkingService] = None) -> FastAPI:
    logging.basicConfig(level=logging.INFO)
    app = FastAPI(title="Parking Lot Management System", version="1.0.0")
    app.state.service = service or build_service()
    app.include_router(router)

    @app.exception_handler(ParkingError)
    def handle_parking_error(_: Request, exc: ParkingError):
        return JSONResponse(status_code=exc.status_code,
                            content={"error": type(exc).__name__, "message": exc.message})

    return app
