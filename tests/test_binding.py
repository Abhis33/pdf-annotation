"""Tests for annotator/binding.py: path resolution (SPEC.md 6.1/6.2/6.3) and
the strict, type-sensitive equality used by checkedWhen/radio-group matching
(SPEC.md 5.6/5.7).

Deliberately not exhaustive: covers the resolution rules actually stated in
the spec (member/index access, missing vs. null, non-object/non-array access)
plus the equality gotchas the spec calls out by name (`1 != "1"`, booleans
distinct from 0/1) rather than every possible path shape.
"""

from annotator.binding import is_missing, resolve_binding, strict_equals

DATA = {
    "taxpayer": {"firstName": "Jordan", "ssn": None},
    "dependents": [
        {"name": "Casey", "qualifiesForCTC": True},
        {"name": "Riley"},
    ],
    "flag": False,
    "count": 0,
}


def test_root_alone_resolves_to_whole_data_set():
    assert resolve_binding("$", DATA) == DATA


def test_member_access_resolves_nested_value():
    assert resolve_binding("$.taxpayer.firstName", DATA) == "Jordan"


def test_index_access_resolves_array_element():
    assert resolve_binding("$.dependents[0].name", DATA) == "Casey"


def test_absent_member_is_missing():
    assert is_missing(resolve_binding("$.taxpayer.middleInitial", DATA))


def test_out_of_range_index_is_missing():
    assert is_missing(resolve_binding("$.dependents[5].name", DATA))


def test_index_access_on_non_array_is_missing():
    assert is_missing(resolve_binding("$.taxpayer.firstName[0]", DATA))


def test_member_access_on_non_object_is_missing():
    assert is_missing(resolve_binding("$.taxpayer.firstName.nested", DATA))


def test_null_value_is_missing():
    """SPEC.md 6.2: 'A resolved JSON null is also treated as missing.'"""
    assert is_missing(resolve_binding("$.taxpayer.ssn", DATA))


def test_falsy_but_present_values_are_not_missing():
    assert resolve_binding("$.flag", DATA) is False
    assert resolve_binding("$.count", DATA) == 0


def test_strict_equals_rejects_numeric_string_against_number():
    assert not strict_equals(1, "1")


def test_strict_equals_distinguishes_bool_from_int():
    assert not strict_equals(True, 1)
    assert not strict_equals(False, 0)


def test_strict_equals_matches_equal_values_of_the_same_type():
    assert strict_equals("single", "single")
    assert strict_equals(1, 1)
    assert strict_equals(True, True)
