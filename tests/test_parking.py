import threading
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from parking_lot.app import build_service, create_app
from parking_lot.core.parking_lot import ParkingLot
from parking_lot.exceptions import (InvalidInputError, LotFullError, PaymentFailedError,
                                    TicketAlreadyClosedError, TicketNotFoundError, VehicleAlreadyParkedError)
from parking_lot.models.floor import Floor
from parking_lot.models.spot import LargeSpot, MediumSpot, SmallSpot
from parking_lot.models.ticket import TicketBuilder
from parking_lot.models.vehicle import Car, VehicleType
from parking_lot.patterns.allocation import BestFitAllocation
from parking_lot.patterns.pricing import EVChargingCharge, FlatPricing, GSTTax, HourlyPricing
from parking_lot.patterns.vehicle_factory import VehicleFactory
from parking_lot.payments import CardPayment, CashPayment, create_payment


class FakeClock:
    def __init__(self):
        self.now = datetime(2026, 11, 20, 10, 0, 0)

    def __call__(self):
        return self.now

    def advance(self, **kwargs):
        self.now += timedelta(**kwargs)


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def service(tmp_path, clock):
    return build_service(str(tmp_path / "test.db"), clock=clock)


def one_medium_spot():
    return [Floor(1, [MediumSpot("F1-M1", 1)])]


# ---------- patterns ----------

def test_singleton_returns_same_instance():
    assert ParkingLot.instance() is ParkingLot.instance()
    with pytest.raises(RuntimeError):
        ParkingLot()


def test_factory_creates_vehicles_and_rejects_unknown():
    assert VehicleFactory.create("car", "dl01").vehicle_type == VehicleType.CAR
    with pytest.raises(InvalidInputError):
        VehicleFactory.create("plane", "X1")
    with pytest.raises(InvalidInputError):
        VehicleFactory.create("CAR", "   ")


def test_builder_requires_fields():
    with pytest.raises(InvalidInputError):
        TicketBuilder().for_vehicle("DL01", VehicleType.CAR).build()


def test_pricing_strategy_and_decorators():
    entry = datetime(2026, 1, 1, 10, 0)
    ticket = (TicketBuilder().for_vehicle("DL01", VehicleType.CAR).at_spot("F1-M1", 1)
              .entered_at(entry).with_ev_charging().build())
    exit_time = entry + timedelta(hours=2, minutes=1)  # 3 started hours
    assert HourlyPricing().calculate(ticket, exit_time) == 90
    assert FlatPricing().calculate(ticket, exit_time) == 100
    assert EVChargingCharge(HourlyPricing()).calculate(ticket, exit_time) == 140
    assert GSTTax(EVChargingCharge(HourlyPricing())).calculate(ticket, exit_time) == 165.2


def test_best_fit_keeps_large_spot_free():
    floors = [Floor(1, [LargeSpot("F1-L1", 1), SmallSpot("F1-S1", 1)])]
    from parking_lot.models.vehicle import Bike
    assert BestFitAllocation().find_spot(floors, Bike("B1")).spot_id == "F1-S1"


# ---------- service ----------

def test_park_and_exit_flow(service, clock):
    ticket = service.park("CAR", "dl01ab1234")
    assert ticket.plate == "DL01AB1234" and ticket.spot_id == "F1-M1"
    assert service.availability()[1]["MEDIUM"] == 2

    clock.advance(minutes=90)
    result = service.exit(ticket.ticket_id, CashPayment())
    assert result.ticket.fee == round(60 * 1.18, 2)  # 2 hours of car parking + GST
    assert service.availability()[1]["MEDIUM"] == 3


def test_same_vehicle_cannot_park_twice(service):
    service.park("CAR", "DL01")
    with pytest.raises(VehicleAlreadyParkedError):
        service.park("CAR", "dl01")


def test_lot_full(tmp_path, clock):
    svc = build_service(str(tmp_path / "t.db"), floors=one_medium_spot(), clock=clock)
    svc.park("CAR", "A1")
    with pytest.raises(LotFullError):
        svc.park("CAR", "A2")
    with pytest.raises(LotFullError):
        svc.park("TRUCK", "T1")  # a truck never fits a medium spot


def test_invalid_and_double_exit(service):
    with pytest.raises(TicketNotFoundError):
        service.exit("nope", CashPayment())
    t = service.park("BIKE", "B1")
    service.exit(t.ticket_id, CashPayment())
    with pytest.raises(TicketAlreadyClosedError):
        service.exit(t.ticket_id, CashPayment())


def test_failed_payment_keeps_ticket_active(service):
    t = service.park("CAR", "C1")
    with pytest.raises(PaymentFailedError):
        service.exit(t.ticket_id, CardPayment("4111111111110000"))
    assert service.exit(t.ticket_id, CashPayment()).ticket.status.value == "PAID"


def test_payment_validation():
    with pytest.raises(InvalidInputError):
        create_payment("CARD", card_number="123")
    with pytest.raises(InvalidInputError):
        create_payment("UPI", upi_id="not-an-upi")


def test_restart_restores_occupied_spots(tmp_path, clock):
    db = str(tmp_path / "t.db")
    build_service(db, floors=one_medium_spot(), clock=clock).park("CAR", "A1")
    restarted = build_service(db, floors=one_medium_spot(), clock=clock)
    with pytest.raises(LotFullError):
        restarted.park("CAR", "A2")


# ---------- concurrency ----------

def test_concurrent_entries_never_share_a_spot(tmp_path, clock):
    svc = build_service(str(tmp_path / "t.db"), floors=one_medium_spot(), clock=clock)
    results, start = [], threading.Barrier(20)

    def worker(i):
        start.wait()
        try:
            svc.park("CAR", f"CAR{i}")
            results.append("ok")
        except LotFullError:
            results.append("full")

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert results.count("ok") == 1 and results.count("full") == 19


def test_concurrent_exits_charge_once(service):
    ticket = service.park("CAR", "C1")
    outcomes, start = [], threading.Barrier(10)

    def worker():
        start.wait()
        try:
            service.exit(ticket.ticket_id, CashPayment())
            outcomes.append("paid")
        except TicketAlreadyClosedError:
            outcomes.append("rejected")

    threads = [threading.Thread(target=worker) for _ in range(10)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert outcomes.count("paid") == 1


# ---------- API ----------

def test_api_end_to_end(service):
    client = TestClient(create_app(service))
    r = client.post("/entry", json={"vehicle_type": "CAR", "plate": "DL01AB1234", "ev_charging": True})
    assert r.status_code == 201
    ticket_id = r.json()["ticket_id"]

    assert client.get(f"/tickets/{ticket_id}/quote").json()["amount_due"] == round(80 * 1.18, 2)
    assert client.get("/availability").json()["free_spots"]["1"]["MEDIUM"] == 2

    r = client.post(f"/exit/{ticket_id}", json={"payment_method": "UPI", "upi_id": "yashi@okaxis"})
    assert r.status_code == 200 and r.json()["ticket"]["status"] == "PAID"


def test_api_errors(service):
    client = TestClient(create_app(service))
    assert client.post("/entry", json={"vehicle_type": "PLANE", "plate": "X"}).status_code == 422
    assert client.post("/exit/missing", json={"payment_method": "CASH"}).status_code == 404
    r = client.post("/entry", json={"vehicle_type": "CAR", "plate": "X"})
    assert client.post("/entry", json={"vehicle_type": "CAR", "plate": "X"}).json()["error"] \
        == "VehicleAlreadyParkedError"
    bad_card = client.post(f"/exit/{r.json()['ticket_id']}",
                           json={"payment_method": "CARD", "card_number": "4111111111110000"})
    assert bad_card.status_code == 402
