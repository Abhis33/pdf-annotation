"""Tests for annotator/styles.py: per-property style resolution
(SPEC.md section 4: field -> defaults -> spec default) and the base-14 PDF
font mapping.
"""

from annotator.styles import SPEC_DEFAULTS, pdf_font_name, resolve_style


def test_no_overrides_falls_back_to_spec_defaults():
    style = resolve_style(None, None)
    assert style["font_family"] == SPEC_DEFAULTS["font"]["family"]
    assert style["font_size"] == SPEC_DEFAULTS["font"]["size"]
    assert style["overflow"] == SPEC_DEFAULTS["overflow"]
    assert style["padding"] == SPEC_DEFAULTS["padding"]


def test_document_defaults_override_spec_defaults():
    defaults = {"font": {"size": 11}, "overflow": "truncate"}
    style = resolve_style(None, defaults)
    assert style["font_size"] == 11
    assert style["overflow"] == "truncate"
    # Untouched properties still fall through to the spec default.
    assert style["font_family"] == SPEC_DEFAULTS["font"]["family"]


def test_field_style_overrides_document_defaults():
    defaults = {"font": {"size": 11}}
    field_style = {"font": {"size": 14}}
    style = resolve_style(field_style, defaults)
    assert style["font_size"] == 14


def test_resolution_is_per_property_not_per_object():
    """A field's `font` override sets only `size`; `family` still falls
    through to defaults rather than being lost with the rest of the object."""
    defaults = {"font": {"family": "Times", "size": 9}}
    field_style = {"font": {"size": 14}}
    style = resolve_style(field_style, defaults)
    assert style["font_size"] == 14
    assert style["font_family"] == "Times"


def test_padding_resolves_independently_per_side():
    defaults = {"padding": {"left": 5}}
    style = resolve_style(None, defaults)
    assert style["padding"]["left"] == 5
    assert style["padding"]["right"] == SPEC_DEFAULTS["padding"]["right"]


def test_pdf_font_name_maps_known_family_and_weight():
    warnings = []
    assert pdf_font_name("Helvetica", "bold", warnings.append) == "Helvetica-Bold"
    assert pdf_font_name("Times", "normal", warnings.append) == "Times-Roman"
    assert warnings == []


def test_pdf_font_name_falls_back_to_helvetica_and_warns():
    warnings = []
    result = pdf_font_name("Comic Sans", "normal", warnings.append)
    assert result == "Helvetica"
    assert len(warnings) == 1
