"""End-to-end smoke tests for annotator/render.py: the SPEC.md sections 3, 5,
7 rendering contract, exercised against small synthetic PDFs built with
reportlab rather than the full examples/f1040.pdf.

Deliberately a handful of representative cases (one success path per major
behavior, one failure path per required-error condition), not a sweep of
every field type/format combination — those are covered at the unit level in
test_binding.py, test_formatting.py, and test_styles.py.
"""

import pytest
from pypdf import PdfReader
from reportlab.pdfgen import canvas

from annotator.render import RenderError, render_pdf

PAGE_SIZE = (300, 300)


def make_blank_pdf(path, pages=1, size=PAGE_SIZE):
    c = canvas.Canvas(str(path), pagesize=size)
    for _ in range(pages):
        c.showPage()
    c.save()
    return path


def base_document(**field_overrides):
    field = {
        "id": "name",
        "type": "text",
        "page": 1,
        "binding": "$.name",
        "rect": {"x": 10, "y": 10, "w": 200, "h": 20},
    }
    field.update(field_overrides)
    return {
        "specVersion": "1.0",
        "form": {"id": "test", "revision": "1"},
        "pages": [{"number": 1, "width": PAGE_SIZE[0], "height": PAGE_SIZE[1]}],
        "fields": [field],
    }


def test_successful_render_writes_expected_text(tmp_path):
    source = make_blank_pdf(tmp_path / "blank.pdf")
    output = tmp_path / "output.pdf"
    warnings = []

    render_pdf(
        base_document(), {"name": "Jordan Rivera"}, source, output, warnings.append
    )

    assert output.is_file()
    reader = PdfReader(str(output))
    assert len(reader.pages) == 1
    assert "Jordan Rivera" in reader.pages[0].extract_text()
    assert warnings == []


def test_required_missing_value_raises_render_error_naming_the_field(tmp_path):
    source = make_blank_pdf(tmp_path / "blank.pdf")
    output = tmp_path / "output.pdf"
    doc = base_document(required=True)

    with pytest.raises(RenderError) as exc_info:
        render_pdf(doc, {}, source, output, lambda msg: None)

    assert len(exc_info.value.all_errors) == 1
    assert exc_info.value.all_errors[0].field_id == "name"
    assert not output.exists()


def test_optional_missing_value_is_skipped_without_error(tmp_path):
    source = make_blank_pdf(tmp_path / "blank.pdf")
    output = tmp_path / "output.pdf"

    render_pdf(base_document(required=False), {}, source, output, lambda msg: None)

    assert output.is_file()


def test_overflow_error_raises_render_error(tmp_path):
    source = make_blank_pdf(tmp_path / "blank.pdf")
    output = tmp_path / "output.pdf"
    doc = base_document(
        rect={"x": 10, "y": 10, "w": 20, "h": 10}, style={"overflow": "error"}
    )

    with pytest.raises(RenderError):
        render_pdf(
            doc,
            {"name": "This value is far too long to fit in a 20-point-wide box"},
            source,
            output,
            lambda msg: None,
        )


def test_checkbox_x_mark_is_drawn_when_checked(tmp_path):
    source = make_blank_pdf(tmp_path / "blank.pdf")
    output = tmp_path / "output.pdf"
    doc = {
        "specVersion": "1.0",
        "form": {"id": "test", "revision": "1"},
        "pages": [{"number": 1, "width": PAGE_SIZE[0], "height": PAGE_SIZE[1]}],
        "fields": [
            {
                "id": "cb",
                "type": "checkbox",
                "page": 1,
                "binding": "$.agree",
                "rect": {"x": 10, "y": 10, "w": 16, "h": 16},
                "checkedWhen": {"truthy": True},
            }
        ],
    }

    render_pdf(doc, {"agree": True}, source, output, lambda msg: None)

    reader = PdfReader(str(output))
    assert "X" in reader.pages[0].extract_text()


def test_page_size_mismatch_warns_but_still_renders(tmp_path):
    source = make_blank_pdf(tmp_path / "blank.pdf", size=(400, 400))
    output = tmp_path / "output.pdf"
    warnings = []

    render_pdf(base_document(), {"name": "Jordan"}, source, output, warnings.append)

    assert output.is_file()
    assert any("annotation declares" in w for w in warnings)
