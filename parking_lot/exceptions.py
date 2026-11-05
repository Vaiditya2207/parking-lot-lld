"""Domain errors. Each carries the HTTP status the API layer should map it to."""


class ParkingError(Exception):
    status_code = 400

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class InvalidInputError(ParkingError):
    status_code = 400


class LotFullError(ParkingError):
    status_code = 409


class VehicleAlreadyParkedError(ParkingError):
    status_code = 409


class TicketNotFoundError(ParkingError):
    status_code = 404


class TicketAlreadyClosedError(ParkingError):
    status_code = 409


class PaymentFailedError(ParkingError):
    status_code = 402


class DemoClockUnavailableError(ParkingError):
    status_code = 404
