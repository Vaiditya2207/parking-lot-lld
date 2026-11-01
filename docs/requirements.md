# Requirements Analysis: Parking Lot Management System

## Problem
A multi-floor parking lot needs to hand out spots to arriving vehicles, issue tickets, charge on exit, and show live free-spot counts at the entrance.

## Actors
| Actor | Description |
|---|---|
| **Driver** | Arrives with a vehicle, receives a ticket, pays on exit. |
| **Attendant** | Operates the entry/exit gate (calls the API on the driver's behalf). |
| **Display Board** | System actor that shows free spots per floor and size. |
| **Payment Provider** | External system that approves or declines card/UPI payments. |

## Functional requirements
1. **FR1 Park:** accept a vehicle (BIKE, CAR, TRUCK) with its number plate and allocate a free spot that fits it.
2. **FR2 Ticket:** issue a ticket with ticket id, plate, spot, floor and entry time.
3. **FR3 Quote:** show the amount due for an active ticket before paying.
4. **FR4 Exit and pay:** calculate the fee, take payment by CASH, CARD or UPI, close the ticket and free the spot.
5. **FR5 Availability:** show free spots per floor and spot size in real time.
6. **FR6 EV charging:** a driver can opt in to EV charging, billed as an add-on.
7. **FR7 Spot fit:** a bike fits any spot, a car fits medium/large, a truck fits only large.

## Non-functional requirements
| Id | Requirement | How it is met |
|---|---|---|
| NFR1 Consistency | Two vehicles must never get the same spot; a ticket is never charged twice. | Lock around allocate+save and around exit; partial unique indexes in the DB. |
| NFR2 Durability | Tickets and payments survive a restart. | SQLite; active tickets are re-loaded into spots on startup. |
| NFR3 Extensibility | New vehicle types, pricing rules and payment methods without editing existing classes. | Factory registry, Strategy, Decorator, PaymentMethod interface. |
| NFR4 Performance | Entry/exit respond in well under 1 s. | In-memory spot search; indexed DB lookups. |
| NFR5 Usability | Clear error messages with correct HTTP codes. | Typed domain exceptions mapped in one handler. |

## Use cases
| Id | Use case | Actor | Main flow | Alternate flows |
|---|---|---|---|---|
| UC1 | Park vehicle | Driver/Attendant | Submit type + plate → spot allocated → ticket returned | Lot full (409); vehicle already inside (409); invalid type/plate (400/422) |
| UC2 | Get quote | Driver | Submit ticket id → amount due | Unknown ticket (404); already paid (409) |
| UC3 | Exit and pay | Driver/Attendant | Submit ticket id + payment → fee charged → spot freed | Payment declined (402, ticket stays active); unknown ticket (404); already paid (409) |
| UC4 | View availability | Display Board | Read free counts per floor/size | — |

## Assumptions
- One physical lot (hence a Singleton).
- Fee = started hours × rate (minimum 1 hour), + ₹50 EV charging if chosen, + 18% GST.
- Rates per hour: Bike ₹10, Car ₹30, Truck ₹60.
- Card numbers ending in `0000` simulate a bank decline in the demo.
