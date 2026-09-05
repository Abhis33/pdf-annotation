"""Field layout and drawing (SPEC.md sections 3, 5, 7)."""

import io

from pypdf import PdfReader, PdfWriter
from reportlab.lib.colors import HexColor
from reportlab.pdfbase.pdfmetrics import getAscent, getDescent, stringWidth
from reportlab.pdfgen import canvas as reportlab_canvas

from .binding import is_missing, resolve_binding, strict_equals
from .formatting import FormatError, format_comb_chars, format_date, format_number
from .styles import pdf_font_name, resolve_style


class RenderError(Exception):
    """A field-level error that must abort the render (SPEC.md: "fail loud")."""

    def __init__(self, field_id, message):
        super().__init__(f"field {field_id!r}: {message}")
        self.field_id = field_id


def render_pdf(document, data, source_pdf_path, output_path, warn):
    """Render `document` (a validated annotation document) with `data` onto
    `source_pdf_path`, writing the result to `output_path`.

    `warn(message)` is called for every non-fatal issue. Raises RenderError
    (collecting every field's error before raising the first, via a list
    attached as `.all_errors`) if any field fails.
    """
    reader = PdfReader(str(source_pdf_path))
    page_specs = {p["number"]: p for p in document["pages"]}

    for number, spec in page_specs.items():
        if number > len(reader.pages):
            raise RenderError(
                "<document>", f"page {number} does not exist in {source_pdf_path}"
            )
        actual = reader.pages[number - 1].mediabox
        if (
            abs(float(actual.width) - spec["width"]) > 1
            or abs(float(actual.height) - spec["height"]) > 1
        ):
            warn(
                f"page {number}: annotation declares "
                f"{spec['width']}x{spec['height']}pt, source PDF page is "
                f"{float(actual.width)}x{float(actual.height)}pt"
            )

    overlay_buffer = io.BytesIO()
    c = reportlab_canvas.Canvas(overlay_buffer)

    errors = []
    fields_by_page = {}
    for field in document["fields"]:
        fields_by_page.setdefault(field["page"], []).append(field)

    for page_number in range(1, len(reader.pages) + 1):
        spec = page_specs.get(page_number)
        width = (
            spec["width"]
            if spec
            else float(reader.pages[page_number - 1].mediabox.width)
        )
        height = (
            spec["height"]
            if spec
            else float(reader.pages[page_number - 1].mediabox.height)
        )
        c.setPageSize((width, height))
        for field in fields_by_page.get(page_number, []):
            try:
                _draw_field(c, field, document.get("defaults"), data, height, warn)
            except RenderError as e:
                errors.append(e)
        c.showPage()

    if errors:
        combined = RenderError("<document>", f"{len(errors)} field(s) failed to render")
        combined.all_errors = errors
        raise combined

    c.save()
    overlay_buffer.seek(0)
    overlay_reader = PdfReader(overlay_buffer)

    writer = PdfWriter()
    for i, page in enumerate(reader.pages):
        page.merge_page(overlay_reader.pages[i])
        writer.add_page(page)
    with open(output_path, "wb") as f:
        writer.write(f)


def _resolve_value(field, data):
    """Apply binding resolution + required/default (SPEC.md 6.3). Returns
    (value, should_skip)."""
    value = resolve_binding(field["binding"], data)
    if is_missing(value):
        if field.get("required", False):
            raise RenderError(field["id"], "required value is missing")
        if "default" in field:
            return field["default"], False
        return None, True
    return value, False


def _draw_field(c, field, defaults, data, page_height, warn):
    value, skip = _resolve_value(field, data)
    if skip:
        return

    field_type = field["type"]
    if field_type == "comb":
        _draw_comb(c, field, value, defaults, page_height, warn)
        return
    if field_type == "checkbox":
        if _checkbox_marked(field["checkedWhen"], value):
            _draw_mark(
                c,
                field["rect"],
                field.get("mark", "X"),
                field.get("style"),
                defaults,
                page_height,
            )
        return
    if field_type == "radio-group":
        for option in field["options"]:
            if strict_equals(option["value"], value):
                _draw_mark(
                    c,
                    option["rect"],
                    field.get("mark", "X"),
                    field.get("style"),
                    defaults,
                    page_height,
                )
                return
        if field.get("required", False):
            raise RenderError(
                field["id"], f"no radio-group option matches value {value!r}"
            )
        return

    try:
        if field_type == "text":
            text = _format_text(field, value)
        elif field_type == "number":
            text = format_number(value, field.get("format", {}), currency=False)
        elif field_type == "currency":
            text = format_number(value, field.get("format", {}), currency=True)
        elif field_type == "date":
            text = format_date(value, field.get("dateFormat", "MM/DD/YYYY"))
        else:
            raise RenderError(field["id"], f"unknown field type {field_type!r}")
    except FormatError as e:
        raise RenderError(field["id"], str(e))

    if text is None:  # zeroFormat: "blank"
        return

    style = resolve_style(field.get("style"), defaults)
    _draw_text(c, field, text, style, page_height, warn)


def _format_text(field, value):
    if not isinstance(value, str):
        raise FormatError(f"expected a string, got {type(value).__name__}")
    if field.get("case") == "upper":
        value = value.upper()
    max_length = field.get("maxLength")
    if max_length is not None and len(value) > max_length:
        value = value[:max_length]
    return value


def _checkbox_marked(checked_when, value):
    if "equals" in checked_when:
        return strict_equals(checked_when["equals"], value)
    return bool(value)


def _to_pdf_y(y, h, page_height):
    """SPEC.md section 3: pdf_y = page.height - y - h (bottom edge of rect)."""
    return page_height - y - h


def _draw_mark(c, rect, mark, field_style, defaults, page_height):
    style = resolve_style(field_style, defaults)
    x, y, w, h = rect["x"], rect["y"], rect["w"], rect["h"]
    pdf_y = _to_pdf_y(y, h, page_height)
    c.setFillColor(HexColor(style["font_color"]))
    if mark == "fill":
        inset_w, inset_h = w * 0.15, h * 0.15
        c.rect(
            x + inset_w,
            pdf_y + inset_h,
            w - 2 * inset_w,
            h - 2 * inset_h,
            fill=1,
            stroke=0,
        )
    elif mark == "check":
        # Drawn as vector strokes rather than a ZapfDingbats glyph: some
        # rasterizers substitute a "missing glyph" box for that font instead
        # of an actual check mark, so a font-independent shape is safer.
        c.setStrokeColor(HexColor(style["font_color"]))
        c.setLineWidth(max(1.0, min(w, h) * 0.12))
        c.setLineJoin(1)
        c.line(x + w * 0.15, pdf_y + h * 0.55, x + w * 0.40, pdf_y + h * 0.25)
        c.line(x + w * 0.40, pdf_y + h * 0.25, x + w * 0.85, pdf_y + h * 0.80)
    else:  # "X"
        font_size = min(w, h) * 0.8
        c.setFont("Helvetica-Bold", font_size)
        c.drawCentredString(x + w / 2, pdf_y + h * 0.25, "X")


def _draw_comb(c, field, value, defaults, page_height, warn):
    try:
        chars = format_comb_chars(value, field["cells"], field.get("fit", "exact"))
    except FormatError as e:
        raise RenderError(field["id"], str(e))

    style = resolve_style(field.get("style"), defaults)
    font_name = pdf_font_name(style["font_family"], style["font_weight"], warn)
    cell_w, cell_h = field["cellSize"]["w"], field["cellSize"]["h"]
    gaps = {g["afterCell"]: g["extra"] for g in field.get("gaps", [])}

    c.setFont(font_name, style["font_size"])
    c.setFillColor(HexColor(style["font_color"]))
    pdf_y = _to_pdf_y(field["cellOrigin"]["y"], cell_h, page_height)
    extra = 0.0
    for i, ch in enumerate(chars, start=1):
        cell_x = field["cellOrigin"]["x"] + (i - 1) * field["pitch"] + extra
        c.drawCentredString(cell_x + cell_w / 2, pdf_y + cell_h * 0.3, ch)
        extra += gaps.get(i, 0)


def _draw_text(c, field, text, style, page_height, warn):
    rect = field["rect"]
    padding = style["padding"]
    padded_x = rect["x"] + padding["left"]
    padded_y = rect["y"] + padding["top"]
    padded_w = rect["w"] - padding["left"] - padding["right"]
    padded_h = rect["h"] - padding["top"] - padding["bottom"]
    pdf_top = page_height - padded_y
    pdf_bottom = pdf_top - padded_h

    font_name = pdf_font_name(style["font_family"], style["font_weight"], warn)
    overflow = style["overflow"]
    multiline = field.get("multiline", False)

    font_size = style["font_size"]
    lines = None
    while True:
        if multiline:
            lines = _wrap_lines(text, font_name, font_size, padded_w)
            fits = _multiline_fits(
                lines, font_name, font_size, style["line_height"], padded_w, padded_h
            )
        else:
            lines = [text]
            fits = (
                stringWidth(text, font_name, font_size) <= padded_w
                and font_size <= padded_h
            )
        if fits or overflow != "shrink" or font_size <= style["min_font_size"]:
            break
        font_size = max(style["min_font_size"], font_size - 0.5)

    if not fits:
        if overflow == "truncate":
            warn(f"field {field['id']!r}: text truncated to fit its box")
            text = _truncate_to_fit(text, font_name, font_size, padded_w)
            lines = [text]
        else:  # "error", or "shrink" that still doesn't fit at minFontSize
            raise RenderError(field["id"], "formatted value does not fit its box")

    c.setFont(font_name, font_size)
    c.setFillColor(HexColor(style["font_color"]))

    if multiline:
        _draw_multiline(
            c,
            lines,
            font_name,
            font_size,
            style,
            padded_x,
            pdf_top,
            pdf_bottom,
            padded_w,
        )
    else:
        _draw_single_line(
            c,
            text,
            font_name,
            font_size,
            style,
            padded_x,
            pdf_top,
            pdf_bottom,
            padded_w,
        )


def _truncate_to_fit(text, font_name, font_size, max_width):
    while text and stringWidth(text, font_name, font_size) > max_width:
        text = text[:-1]
    return text


def _wrap_lines(text, font_name, font_size, max_width):
    words = text.split()
    if not words:
        return [""]
    lines, current = [], words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if stringWidth(candidate, font_name, font_size) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _multiline_fits(lines, font_name, font_size, line_height, max_width, max_height):
    widths_ok = all(
        stringWidth(line, font_name, font_size) <= max_width for line in lines
    )
    block_height = len(lines) * font_size * line_height
    return widths_ok and block_height <= max_height


def _line_x(line, font_name, font_size, alignment, padded_x, padded_w):
    width = stringWidth(line, font_name, font_size)
    if alignment == "center":
        return padded_x + (padded_w - width) / 2
    if alignment == "right":
        return padded_x + padded_w - width
    return padded_x


def _draw_single_line(
    c, text, font_name, font_size, style, padded_x, pdf_top, pdf_bottom, padded_w
):
    ascent = getAscent(font_name) / 1000 * font_size
    descent = getDescent(font_name) / 1000 * font_size
    text_height = ascent - descent
    valign = style["vertical_alignment"]
    if valign == "top":
        baseline = pdf_top - ascent
    elif valign == "bottom":
        baseline = pdf_bottom - descent
    else:
        baseline = pdf_bottom + (pdf_top - pdf_bottom - text_height) / 2 - descent
    x = _line_x(text, font_name, font_size, style["text_alignment"], padded_x, padded_w)
    c.drawString(x, baseline, text)


def _draw_multiline(
    c, lines, font_name, font_size, style, padded_x, pdf_top, pdf_bottom, padded_w
):
    ascent = getAscent(font_name) / 1000 * font_size
    descent = getDescent(font_name) / 1000 * font_size
    text_height = ascent - descent
    line_spacing = font_size * style["line_height"]
    block_height = (len(lines) - 1) * line_spacing + text_height

    padded_h = pdf_top - pdf_bottom
    valign = style["vertical_alignment"]
    if valign == "top":
        first_baseline = pdf_top - ascent
    elif valign == "bottom":
        first_baseline = pdf_bottom - descent + (len(lines) - 1) * line_spacing
    else:
        first_baseline = (
            pdf_bottom
            + (padded_h - block_height) / 2
            - descent
            + (len(lines) - 1) * line_spacing
        )

    for i, line in enumerate(lines):
        baseline = first_baseline - i * line_spacing
        x = _line_x(
            line, font_name, font_size, style["text_alignment"], padded_x, padded_w
        )
        c.drawString(x, baseline, line)
