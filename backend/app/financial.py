from __future__ import annotations

from decimal import Decimal, InvalidOperation

PAISE_PER_RUPEE = Decimal("100")


def to_paise(value: Decimal | str | int | float) -> int:
    """Convert a rupee amount with at most two fractional digits into paise."""
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise ValueError("Money value must be a finite decimal amount.") from error

    if not amount.is_finite():
        raise ValueError("Money value must be a finite decimal amount.")
    if amount.as_tuple().exponent < -2:
        raise ValueError("Money amounts may have no more than two decimal places.")

    return int(amount * PAISE_PER_RUPEE)


def from_paise(value: int) -> Decimal:
    return Decimal(value) / PAISE_PER_RUPEE


def normalize_invoice_number(invoice_number: str) -> str:
    return invoice_number.strip().upper()
