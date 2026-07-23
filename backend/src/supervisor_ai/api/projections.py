from decimal import Decimal


def decimal_string(value: Decimal) -> str:
    """Projeta Decimal financeiro sem passagem por float."""
    whole, separator, fraction = format(value, "f").partition(".")
    if not separator:
        return f"{whole}.00"
    significant = fraction.rstrip("0")
    return f"{whole}.{significant.ljust(2, '0')}"
