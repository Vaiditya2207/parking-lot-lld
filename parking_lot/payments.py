"""Payment methods. Each one is a small class behind one interface (polymorphism, Interface Segregation)."""
import re
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from parking_lot.exceptions import InvalidInputError, PaymentFailedError


@dataclass(frozen=True)
class PaymentReceipt:
    payment_id: str
    method: str
    amount: float
    reference: str


class PaymentMethod(ABC):
    name: str

    @abstractmethod
    def pay(self, amount: float) -> PaymentReceipt: ...

    def _receipt(self, amount: float, reference: str) -> PaymentReceipt:
        return PaymentReceipt(str(uuid.uuid4()), self.name, amount, reference)


class CashPayment(PaymentMethod):
    name = "CASH"

    def pay(self, amount):
        return self._receipt(amount, "cash-counter")


class CardPayment(PaymentMethod):
    name = "CARD"

    def __init__(self, card_number: Optional[str]):
        if not card_number or not re.fullmatch(r"\d{16}", card_number):
            raise InvalidInputError("Card number must be 16 digits")
        self._card_number = card_number

    def pay(self, amount):
        # Demo rule standing in for a bank decline: cards ending in 0000 are declined.
        if self._card_number.endswith("0000"):
            raise PaymentFailedError("Card was declined")
        return self._receipt(amount, f"card-****{self._card_number[-4:]}")


class UPIPayment(PaymentMethod):
    name = "UPI"

    def __init__(self, upi_id: Optional[str]):
        if not upi_id or not re.fullmatch(r"[\w.\-]+@[\w]+", upi_id):
            raise InvalidInputError("UPI id must look like name@bank")
        self._upi_id = upi_id

    def pay(self, amount):
        return self._receipt(amount, f"upi-{self._upi_id}")


def create_payment(method: str, card_number: Optional[str] = None, upi_id: Optional[str] = None) -> PaymentMethod:
    method = (method or "").upper()
    if method == "CASH":
        return CashPayment()
    if method == "CARD":
        return CardPayment(card_number)
    if method == "UPI":
        return UPIPayment(upi_id)
    raise InvalidInputError("Payment method must be CASH, CARD or UPI")
