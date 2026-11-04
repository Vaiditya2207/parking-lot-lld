# Diagrams

All diagrams are Mermaid. They render on GitHub, or paste them into https://mermaid.live to export PNGs.

## 1. Use case diagram

```mermaid
flowchart LR
    Driver([Driver])
    Attendant([Attendant])
    Board([Display Board])
    PayProv([Payment Provider])
    subgraph System[Parking Lot System]
        UC1((Park vehicle))
        UC2((Get quote))
        UC3((Exit and pay))
        UC4((View availability))
    end
    Driver --- UC1
    Driver --- UC2
    Driver --- UC3
    Attendant --- UC1
    Attendant --- UC3
    Board --- UC4
    UC3 --- PayProv
```

## 2. Class diagram

```mermaid
classDiagram
    direction LR

    class Vehicle {
        <<abstract>>
        -_plate: str
        +plate: str
        +vehicle_type: VehicleType*
        +required_spot_size: SpotSize*
    }
    class Bike
    class Car
    class Truck
    Vehicle <|-- Bike
    Vehicle <|-- Car
    Vehicle <|-- Truck

    class ParkingSpot {
        <<abstract>>
        -_spot_id: str
        -_floor_number: int
        -_vehicle: Vehicle
        +size: SpotSize*
        +is_free() bool
        +can_fit(v: Vehicle) bool
        +assign(v: Vehicle)
        +release()
    }
    class SmallSpot
    class MediumSpot
    class LargeSpot
    ParkingSpot <|-- SmallSpot
    ParkingSpot <|-- MediumSpot
    ParkingSpot <|-- LargeSpot

    class Floor {
        -_number: int
        -_spots: List~ParkingSpot~
        +free_spots() List~ParkingSpot~
    }

    class ParkingLot {
        <<singleton>>
        -_instance: ParkingLot$
        -_floors: List~Floor~
        -_observers: List~SpotObserver~
        -_allocation: SpotAllocationStrategy
        +lock: RLock
        +instance()$ ParkingLot
        +add_floor(f: Floor)
        +subscribe(o: SpotObserver)
        +park(v: Vehicle) ParkingSpot
        +release(spot_id: str)
    }

    class Ticket {
        +ticket_id: str
        +plate: str
        +vehicle_type: VehicleType
        +spot_id: str
        +entry_time: datetime
        +exit_time: datetime
        +ev_charging: bool
        +fee: float
        +status: TicketStatus
        +close(exit_time, fee)
    }
    class TicketBuilder {
        +for_vehicle(plate, type) TicketBuilder
        +at_spot(spot_id, floor) TicketBuilder
        +entered_at(t) TicketBuilder
        +with_ev_charging(b) TicketBuilder
        +build() Ticket
    }
    class VehicleFactory {
        <<factory>>
        +create(type, plate)$ Vehicle
        +register(type, cls)$
    }

    class SpotAllocationStrategy {
        <<interface>>
        +find_spot(floors, v) ParkingSpot
    }
    class NearestFirstAllocation
    class BestFitAllocation
    SpotAllocationStrategy <|.. NearestFirstAllocation
    SpotAllocationStrategy <|.. BestFitAllocation

    class PricingStrategy {
        <<interface>>
        +calculate(ticket, exit_time) float
    }
    class HourlyPricing
    class FlatPricing
    class PricingDecorator {
        <<abstract>>
        -_inner: PricingStrategy
    }
    class EVChargingCharge
    class GSTTax
    PricingStrategy <|.. HourlyPricing
    PricingStrategy <|.. FlatPricing
    PricingStrategy <|.. PricingDecorator
    PricingDecorator <|-- EVChargingCharge
    PricingDecorator <|-- GSTTax
    PricingDecorator o-- "1" PricingStrategy : wraps

    class SpotObserver {
        <<interface>>
        +on_spot_changed(e: SpotEvent)
    }
    class DisplayBoard
    class AuditLogger
    SpotObserver <|.. DisplayBoard
    SpotObserver <|.. AuditLogger

    class PaymentMethod {
        <<interface>>
        +pay(amount) PaymentReceipt
    }
    class CashPayment
    class CardPayment
    class UPIPayment
    PaymentMethod <|.. CashPayment
    PaymentMethod <|.. CardPayment
    PaymentMethod <|.. UPIPayment

    class TicketRepository {
        <<interface>>
        +save(t) +update(t) +get(id) +find_active_by_plate(p)
    }
    class PaymentRepository {
        <<interface>>
        +save(ticket_id, receipt, paid_at)
    }
    class SqliteTicketRepository
    class SqlitePaymentRepository
    TicketRepository <|.. SqliteTicketRepository
    PaymentRepository <|.. SqlitePaymentRepository

    class ParkingService {
        +park(type, plate, ev) Ticket
        +quote(ticket_id) float
        +exit(ticket_id, payment) ExitResult
        +availability() dict
    }
    class ParkingController {
        POST /entry
        GET /tickets/id/quote
        POST /exit/id
        GET /availability
    }

    ParkingLot "1" *-- "1..*" Floor : owns
    Floor "1" *-- "1..*" ParkingSpot : owns
    ParkingSpot "1" o-- "0..1" Vehicle : holds
    ParkingLot "1" o-- "0..*" SpotObserver : notifies
    ParkingLot "1" --> "1" SpotAllocationStrategy : uses
    TicketBuilder ..> Ticket : creates
    VehicleFactory ..> Vehicle : creates
    Ticket "0..*" --> "1" ParkingSpot : for spot
    ParkingController --> ParkingService
    ParkingService --> ParkingLot
    ParkingService --> TicketRepository
    ParkingService --> PaymentRepository
    ParkingService --> PricingStrategy
    ParkingService ..> PaymentMethod : uses
```

**Relationships:** composition (lot owns floors, floor owns spots), aggregation (spot holds a vehicle that exists on its own; a decorator wraps a strategy), association (ticket → spot, service → repositories), inheritance/realisation (vehicle, spot, strategy, observer, payment hierarchies), dependency (builder/factory create objects).

## 3. Sequence diagram: vehicle entry (UC1)

```mermaid
sequenceDiagram
    actor A as Attendant
    participant C as ParkingController
    participant S as ParkingService
    participant F as VehicleFactory
    participant L as ParkingLot
    participant AS as AllocationStrategy
    participant B as DisplayBoard
    participant R as TicketRepository

    A->>C: POST /entry {CAR, DL01AB1234}
    C->>S: park("CAR", "DL01AB1234")
    S->>F: create("CAR", plate)
    F-->>S: Car
    S->>L: acquire lock
    S->>R: find_active_by_plate(plate)
    R-->>S: none
    S->>L: park(car)
    L->>AS: find_spot(floors, car)
    AS-->>L: spot F1-M1
    L->>L: spot.assign(car)
    L-)B: on_spot_changed(occupied)
    L-->>S: spot
    S->>S: TicketBuilder...build()
    S->>R: save(ticket)
    S->>L: release lock
    S-->>C: Ticket
    C-->>A: 201 TicketResponse
    Note over S,L: If no spot: LotFullError → 409.<br/>If save fails: spot released (rollback).
```

## 4. Sequence diagram: exit and pay (UC3)

```mermaid
sequenceDiagram
    actor A as Attendant
    participant C as ParkingController
    participant S as ParkingService
    participant R as TicketRepository
    participant P as PricingStrategy (GST(EV(Hourly)))
    participant M as PaymentMethod
    participant PR as PaymentRepository
    participant L as ParkingLot
    participant B as DisplayBoard

    A->>C: POST /exit/{id} {UPI, upi_id}
    C->>C: create_payment("UPI", ...)
    C->>S: exit(id, payment)
    S->>L: acquire lock
    S->>R: get(id)
    R-->>S: ticket (ACTIVE)
    S->>P: calculate(ticket, now)
    P-->>S: fee
    S->>M: pay(fee)
    M-->>S: receipt
    S->>S: ticket.close(now, fee)
    S->>R: update(ticket)
    S->>PR: save(receipt)
    S->>L: release(spot_id)
    L-)B: on_spot_changed(free)
    S->>L: release lock
    S-->>C: ExitResult
    C-->>A: 200 ExitResponse
    Note over S,M: Declined payment → 402, ticket stays ACTIVE, spot stays taken.
```

## 5. Activity diagram: full visit

```mermaid
flowchart TD
    Start([Vehicle arrives]) --> V{Valid type and plate?}
    V -- no --> E1[400/422 error] --> End1([Turned away])
    V -- yes --> D{Already parked?}
    D -- yes --> E2[409 VehicleAlreadyParked] --> End1
    D -- no --> Spot{Free spot that fits?}
    Spot -- no --> E3[409 LotFull] --> End1
    Spot -- yes --> Assign[Assign spot, notify display board]
    Assign --> Ticket[Build and save ticket]
    Ticket --> Parked[Vehicle parked]
    Parked --> Exit[Driver returns with ticket]
    Exit --> Fee[Calculate fee: hourly + EV + GST]
    Fee --> Pay{Payment approved?}
    Pay -- no --> Retry[402, ticket stays ACTIVE] --> Fee
    Pay -- yes --> Close[Close ticket, save payment]
    Close --> Free[Free spot, notify display board]
    Free --> End2([Vehicle leaves])
```

## 6. ER diagram (database schema)

```mermaid
erDiagram
    FLOORS ||--|{ SPOTS : contains
    SPOTS ||--o{ TICKETS : "issued for"
    TICKETS ||--o| PAYMENTS : "paid by"

    FLOORS {
        int floor_number PK
    }
    SPOTS {
        text spot_id PK
        int floor_number FK
        text size "SMALL | MEDIUM | LARGE"
    }
    TICKETS {
        text ticket_id PK
        text plate "unique while ACTIVE"
        text vehicle_type "BIKE | CAR | TRUCK"
        text spot_id FK "unique while ACTIVE"
        text entry_time
        text exit_time
        int ev_charging
        real fee
        text status "ACTIVE | PAID"
    }
    PAYMENTS {
        text payment_id PK
        text ticket_id FK "UNIQUE"
        text method "CASH | CARD | UPI"
        real amount
        text reference
        text paid_at
    }
```

**Indexes:** `ux_active_ticket_per_spot` and `ux_active_ticket_per_plate` (partial unique indexes on `status = 'ACTIVE'`) stop double allocation even if application code had a bug; `ix_tickets_status` speeds up loading active tickets on restart.
