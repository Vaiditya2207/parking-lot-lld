# Parking Lot Management System (LLD Capstone)

A multi-floor parking lot: vehicles get a spot and a ticket on entry, pay on exit (cash, card or UPI), and a display board shows free spots live. Built to cover every Low-Level Design point in the capstone rubric.

**Stack:** Python 3, FastAPI, SQLite, pytest.

## Run it

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py            # open http://127.0.0.1:8000/docs for the interactive demo
pytest -q                 # 16 tests, including concurrency tests
```

### Demo script (2 minutes)

```bash
# 1. Park a car with EV charging
curl -X POST localhost:8000/entry -H 'content-type: application/json' \
     -d '{"vehicle_type":"CAR","plate":"DL01AB1234","ev_charging":true}'
# 2. Board updates: floor 1 MEDIUM drops from 3 to 2
curl localhost:8000/availability
# 3. Quote, then pay by UPI
curl localhost:8000/tickets/<ticket_id>/quote
curl -X POST localhost:8000/exit/<ticket_id> -H 'content-type: application/json' \
     -d '{"payment_method":"UPI","upi_id":"demo@okaxis"}'
# 4. Edge cases: pay again (409), unknown ticket (404), declined card ending 0000 (402),
#    park the same plate twice (409)
```

## Project structure

```
parking_lot/
  models/        Vehicle, ParkingSpot (abstract) + subclasses, Floor, Ticket + TicketBuilder
  patterns/      VehicleFactory, pricing (Strategy + Decorator), allocation (Strategy), observer
  core/          ParkingLot (Singleton, Observer subject, holds the lock)
  payments.py    PaymentMethod interface: Cash, Card, UPI
  repository/    Repository interfaces + SQLite implementations, DB schema
  service/       ParkingService: business rules, locking
  api/           Controller (FastAPI routes) + request/response schemas
  app.py         Composition root: wires concrete classes together
  exceptions.py  Domain errors with HTTP status codes
docs/
  requirements.md   Actors, functional/non-functional requirements, use cases
  diagrams.md       Use case, class, 2 sequence, activity and ER diagrams (Mermaid)
tests/              Unit, service, concurrency and API tests
```

## Rubric mapping

| # | Rubric item | Where |
|---|---|---|
| 1 | Requirement Analysis | `docs/requirements.md`: 4 actors, 7 FRs, 5 NFRs, 4 use cases with alternate flows |
| 2 | Class Diagram | `docs/diagrams.md` §2: all classes, attributes, methods; composition, aggregation, association, inheritance, multiplicities |
| 3 | OOP | Abstract `Vehicle`, `ParkingSpot`, `PricingDecorator`; interfaces `PricingStrategy`, `SpotAllocationStrategy`, `SpotObserver`, `PaymentMethod`, repositories; private fields with read-only properties; polymorphic `calculate()`, `pay()`, `can_fit()` |
| 4 | SOLID | See the table below |
| 5 | Design Patterns | See the table below |
| 6 | Sequence / Activity | `docs/diagrams.md` §3–5 |
| 7 | API / Interface Design | `parking_lot/api/`: typed request/response models; Controller → Service → Repository |
| 8 | Database Schema | `docs/diagrams.md` §6 + `SCHEMA` in `repository/repositories.py`: PKs, FKs, CHECKs, partial unique indexes |
| 9 | Errors, Validation, Concurrency | `exceptions.py`, input validation (pydantic, factory, payments), lock in `ParkingService`, DB unique indexes, `tests/test_parking.py::test_concurrent_*` |
| 10 | Working Implementation | `python main.py` + `/docs`; 16 passing tests |

### Design patterns and why

| Pattern | Class | Why it fits |
|---|---|---|
| **Singleton** (creational) | `ParkingLot.instance()` | There is one physical lot; all requests must see the same spots and share one lock. Double-checked locking makes creation thread-safe. |
| **Factory** (creational) | `VehicleFactory` | The API receives a type string; callers should not know concrete classes. New types are added with `register()`. |
| **Builder** (creational) | `TicketBuilder` | A ticket has many required and optional fields; the builder reads clearly and validates once in `build()`. |
| **Strategy** (behavioural) | `PricingStrategy` (`HourlyPricing`, `FlatPricing`), `SpotAllocationStrategy` (`NearestFirst`, `BestFit`) | Pricing and allocation rules change by business need; swap them without touching the service. |
| **Decorator** (structural) | `EVChargingCharge`, `GSTTax` | Add-on charges stack on any base price: `GSTTax(EVChargingCharge(HourlyPricing()))`. No subclass explosion like `HourlyWithEVAndGST`. |
| **Observer** (behavioural) | `ParkingLot` → `DisplayBoard`, `AuditLogger` | The lot does not need to know who cares about spot changes; new listeners just subscribe. |
| **Repository** (architectural) | `TicketRepository`, `PaymentRepository` | Hides SQL from business logic; enables swapping the database. |

### SOLID, with the exact place each is applied

| Principle | Where |
|---|---|
| **S**ingle Responsibility | `ParkingService` = rules, `SqliteTicketRepository` = persistence, `controller.py` = HTTP, pricing classes = fee math, `DisplayBoard` = counts. |
| **O**pen/Closed | New vehicle via `VehicleFactory.register()`; new pricing rule = new `PricingStrategy`/decorator; new payment = new `PaymentMethod`. Nothing existing is edited. |
| **L**iskov Substitution | Any `Vehicle` works in `can_fit()`/`park()`; any `PricingStrategy` (including decorated ones) works in `ParkingService`; tests swap repos and clocks freely. |
| **I**nterface Segregation | Small interfaces: `SpotObserver` has one method, `PaymentMethod` one, `PricingStrategy` one; tickets and payments have separate repositories. |
| **D**ependency Inversion | `ParkingService` receives abstractions (`TicketRepository`, `PricingStrategy`, clock) through its constructor; only `app.py` picks concrete classes. |

### Concurrency and edge cases

| Scenario | Behaviour |
|---|---|
| 20 cars race for the last spot | Exactly 1 gets it, 19 get `409 LotFull` (lock around find-spot + save). Tested. |
| Same ticket paid twice at once | Charged once; others get `409 TicketAlreadyClosed`. Tested. |
| Same plate enters twice | `409 VehicleAlreadyParked` (service check + DB partial unique index). |
| Card declined | `402`; ticket stays ACTIVE and spot stays taken so the driver can retry. |
| DB write fails after spot assigned | Spot is released (rollback). |
| Server restarts with cars inside | Active tickets are reloaded and their spots marked taken. |
| Invalid input | Unknown vehicle type / empty plate / bad card / bad UPI → `400` or `422` with a clear message. |

## Team contributions

| Member | Work |
|---|---|
| Vaiditya | Domain models (vehicles, spots, floors), exceptions, ticket builder and vehicle factory, `ParkingLot` singleton with allocation strategies and observers, `ParkingService` with locking, tests |
| Yashi Gupta | Requirements analysis, pricing strategies and decorators, payment methods, repository layer and DB schema, REST API, UML diagrams, README |
