"""Style resolution (SPEC.md section 4): field -> defaults -> spec default,
resolved per-property, plus mapping resolved styles onto reportlab fonts."""

SPEC_DEFAULTS = {
    "font": {"family": "Helvetica", "size": 9, "weight": "normal", "color": "#000000"},
    "textAlignment": "left",
    "verticalAlignment": "middle",
    "padding": {"left": 2, "right": 2, "top": 2, "bottom": 2},
    "overflow": "shrink",
    "minFontSize": 5,
    "lineHeight": 1.15,
}

# Base-14 fonts available in every PDF without embedding. Unknown families
# fall back to Helvetica (SPEC.md 4: "renderers MUST substitute a metrically
# similar font if unavailable").
_FONT_FAMILIES = {
    "helvetica": {"normal": "Helvetica", "bold": "Helvetica-Bold"},
    "times": {"normal": "Times-Roman", "bold": "Times-Bold"},
    "times-roman": {"normal": "Times-Roman", "bold": "Times-Bold"},
    "courier": {"normal": "Courier", "bold": "Courier-Bold"},
}


def resolve_style(field_style, defaults):
    """Merge `field_style`, `defaults`, and the spec defaults, one property
    at a time (SPEC.md section 4: field -> defaults -> spec default)."""
    field_style = field_style or {}
    defaults = defaults or {}

    def prop(key, sub=None):
        for source in (field_style, defaults):
            if key in source and (sub is None or sub in source[key]):
                return source[key][sub] if sub else source[key]
        return SPEC_DEFAULTS[key][sub] if sub else SPEC_DEFAULTS[key]

    padding = {side: prop("padding", side) for side in SPEC_DEFAULTS["padding"]}

    return {
        "font_family": prop("font", "family"),
        "font_size": prop("font", "size"),
        "font_weight": prop("font", "weight"),
        "font_color": prop("font", "color"),
        "text_alignment": prop("textAlignment"),
        "vertical_alignment": prop("verticalAlignment"),
        "padding": padding,
        "overflow": prop("overflow"),
        "min_font_size": prop("minFontSize"),
        "line_height": prop("lineHeight"),
    }


def pdf_font_name(family, weight, warn):
    variants = _FONT_FAMILIES.get(family.lower())
    if variants is None:
        warn(f"unknown font family {family!r}; substituting Helvetica")
        variants = _FONT_FAMILIES["helvetica"]
    return variants.get(weight, variants["normal"])
