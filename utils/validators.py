from datetime import date
from decimal import Decimal, InvalidOperation


class ValidationError(ValueError):
    pass


def required(value: str, label: str, maximum: int = 255) -> str:
    value = (value or "").strip()
    if not value or len(value) > maximum:
        raise ValidationError(f"{label} is required and must be at most {maximum} characters")
    return value


def money(value, *, positive=False) -> Decimal:
    if isinstance(value, (float, bool)):
        raise ValidationError("Use a decimal monetary amount")
    try:
        result = Decimal(value)
        if not result.is_finite() or result < 0 or result >= Decimal("10000000000"):
            raise ValidationError("Amount is outside the allowed range")
        if result.as_tuple().exponent < -2 and result != result.quantize(Decimal("0.01")):
            raise ValidationError("Amounts may have at most two decimal places")
        if positive and result == 0:
            raise ValidationError("Payment must be greater than zero")
        return result.quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValidationError("Enter a valid monetary amount") from exc


def dates(start: date | None, end: date | None):
    if start and end and end < start:
        raise ValidationError("End date must not precede start date")
