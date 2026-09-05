"""Binding-path resolution against a caller's data set (SPEC.md section 6)."""

import re

_SEGMENT = re.compile(r"\.([A-Za-z_][A-Za-z0-9_]*)(?:\[(\d+)\])?")

_MISSING = object()


def resolve_binding(binding, data):
    """Resolve a `$`-rooted binding path against `data`.

    Returns the resolved JSON value, or `_MISSING` if any segment fails to
    resolve (absent member, out-of-range index, non-object/non-array access,
    or a resolved `null` - SPEC.md section 6.2/6.3).
    """
    value = data
    pos = 1  # binding always starts with "$" (enforced by the schema pattern)
    while pos < len(binding):
        m = _SEGMENT.match(binding, pos)
        name, index = m.group(1), m.group(2)
        if not isinstance(value, dict) or name not in value:
            return _MISSING
        value = value[name]
        if index is not None:
            i = int(index)
            if not isinstance(value, list) or i >= len(value):
                return _MISSING
            value = value[i]
        pos = m.end()
    return _MISSING if value is None else value


def is_missing(value):
    return value is _MISSING


def strict_equals(a, b):
    """Type-sensitive equality: `1 != "1"`, and `True`/`False` are distinct
    from the numbers 1/0 (SPEC.md 5.6/5.7 "strict, type-sensitive equality")."""
    if isinstance(a, bool) != isinstance(b, bool):
        return False
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a == b
    return type(a) is type(b) and a == b
