"""Tests for annotator/formatting.py: number/currency formatting rules
(SPEC.md 7.1), date token substitution (SPEC.md 5.4), and comb-value
character stripping/length validation (SPEC.md 5.5).

Deliberately not exhaustive: covers each formatting rule the spec states
explicitly (half-away-from-zero rounding, both negative formats, all three
zero formats, comb strip + both fit modes) rather than every option
combination.
"""

import pytest

from annotator.formatting import (
    FormatError,
    format_comb_chars,
    format_date,
    format_number,
)


def test_currency_rounds_half_away_from_zero_for_positive_values():
    """SPEC.md 5.3: 50 cents rounds to the next dollar."""
    assert format_number(1234.5, {}, currency=True) == "1,235"


def test_currency_rounds_half_away_from_zero_for_negative_values():
    """SPEC.md 5.3: -$1.50 rounds to -$2, not -$1."""
    assert format_number(-1.5, {"negativeFormat": "minus"}, currency=True) == "-2"


def test_currency_default_negative_format_is_parentheses():
    assert format_number(-1234, {}, currency=True) == "(1,234)"


def test_number_default_negative_format_is_minus():
    assert format_number(-1234, {}, currency=False) == "-1,234"


def test_thousands_separator_can_be_disabled():
    fmt = {"thousandsSeparator": False}
    assert format_number(1234, fmt, currency=False) == "1234"


def test_currency_symbol_is_prefixed_when_requested():
    fmt = {"currencySymbol": True}
    assert format_number(1234, fmt, currency=True) == "$1,234"


def test_decimal_places_are_respected():
    fmt = {"decimalPlaces": 2}
    assert format_number(1234.5, fmt, currency=True) == "1,234.50"


def test_zero_format_print_is_the_default():
    assert format_number(0, {}, currency=True) == "0"


def test_zero_format_blank_returns_none_to_signal_skip():
    assert format_number(0, {"zeroFormat": "blank"}, currency=True) is None


def test_zero_format_dash_returns_em_dash():
    assert format_number(0, {"zeroFormat": "dash"}, currency=True) == "—"


def test_non_numeric_value_raises_format_error():
    with pytest.raises(FormatError):
        format_number("1234", {}, currency=True)


def test_boolean_value_raises_format_error():
    """bool is a numeric subtype in Python; the spec requires a JSON number."""
    with pytest.raises(FormatError):
        format_number(True, {}, currency=False)


def test_date_default_format_is_mm_dd_yyyy():
    assert format_date("2026-04-10", "MM/DD/YYYY") == "04/10/2026"


def test_date_custom_token_template():
    assert format_date("2026-04-10", "YYYY-MM-DD") == "2026-04-10"


def test_date_two_digit_year_token():
    assert format_date("2026-04-10", "MM/DD/YY") == "04/10/26"


def test_date_rejects_non_iso_input():
    with pytest.raises(FormatError):
        format_date("04/10/2026", "MM/DD/YYYY")


def test_comb_strips_punctuation_before_counting_cells():
    assert format_comb_chars("123-45-6789", 9, "exact") == list("123456789")


def test_comb_exact_fit_rejects_wrong_length():
    with pytest.raises(FormatError):
        format_comb_chars("123456", 9, "exact")


def test_comb_left_fit_allows_fewer_characters_than_cells():
    assert format_comb_chars("42", 17, "left") == ["4", "2"]


def test_comb_left_fit_rejects_more_characters_than_cells():
    with pytest.raises(FormatError):
        format_comb_chars("123456789", 5, "left")
