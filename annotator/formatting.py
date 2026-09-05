"""Value formatting rules (SPEC.md section 7.1)."""

import re
from decimal import ROUND_HALF_UP, Decimal

DASH = "—"  # em dash, used for zeroFormat "dash"

_CURRENCY_SYMBOLS = {"USD": "$"}

_DATE_TOKENS = re.compile(r"YYYY|YY|MM|DD")


class FormatError(Exception):
    """Raised when a bound value cannot be formatted as its field type requires."""


def format_number(value, fmt, currency=False):
    """Format a number per SPEC.md 7.1. `fmt` is the field's resolved
    number/currency format dict. Returns None if the field should be skipped
    (zeroFormat "blank" on an exact zero)."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise FormatError(f"expected a JSON number, got {type(value).__name__}")

    decimal_places = fmt.get("decimalPlaces", 0)
    thousands = fmt.get("thousandsSeparator", True)
    negative_format = fmt.get("negativeFormat", "parentheses" if currency else "minus")
    zero_format = fmt.get("zeroFormat", "print")

    quantum = Decimal(1).scaleb(-decimal_places)
    rounded = Decimal(str(value)).quantize(quantum, rounding=ROUND_HALF_UP)

    if rounded == 0:
        if zero_format == "blank":
            return None
        if zero_format == "dash":
            return DASH

    is_negative = rounded < 0
    magnitude = -rounded if is_negative else rounded

    int_part, _, frac_part = f"{magnitude:.{decimal_places}f}".partition(".")
    if thousands:
        int_part = f"{int(int_part):,}"
    text = int_part if decimal_places == 0 else f"{int_part}.{frac_part}"

    if currency and fmt.get("currencySymbol", False):
        symbol = _CURRENCY_SYMBOLS.get(
            fmt.get("currency", "USD"), fmt.get("currency", "USD") + " "
        )
        text = symbol + text

    if is_negative:
        text = f"({text})" if negative_format == "parentheses" else f"-{text}"

    return text


def format_date(value, date_format):
    """Format an ISO-8601 date string per a `dateFormat` template (SPEC.md 5.4)."""
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", value or "")
    if not m:
        raise FormatError(f"expected an ISO-8601 date (YYYY-MM-DD), got {value!r}")
    year, month, day = m.group(1), m.group(2), m.group(3)

    def replace(tok):
        return {"YYYY": year, "YY": year[2:], "MM": month, "DD": day}[tok.group(0)]

    return _DATE_TOKENS.sub(replace, date_format)


def format_comb_chars(value, cells, fit):
    """Strip non-alphanumeric characters and validate length per SPEC.md 5.5.
    Returns the list of characters to place in cells 1..len (left-filled)."""
    chars = re.sub(r"[^A-Za-z0-9]", "", str(value))
    if fit == "exact" and len(chars) != cells:
        raise FormatError(
            f"comb value has {len(chars)} character(s), expected exactly {cells}"
        )
    if fit == "left" and len(chars) > cells:
        raise FormatError(
            f"comb value has {len(chars)} character(s), expected at most {cells}"
        )
    return list(chars)
