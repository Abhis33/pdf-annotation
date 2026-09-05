# pdf-annotation

A specification for annotating fields and boxes on U.S. tax forms, so that any
application, using its own proprietary code, can print values from a nested data set
into exactly the right boxes on the form.

| Path | What it is |
|------|------------|
| [`SPEC.md`](SPEC.md) | **The specification.** Coordinate system, field types, formatting rules, the data-binding grammar, and the rendering contract an implementation must follow. |
| [`schema/annotation.schema.json`](schema/annotation.schema.json) | JSON Schema (draft 2020-12) for validating annotation documents. |
| [`examples/f1040-simplified.annotation.json`](examples/f1040-simplified.annotation.json) | A worked annotation of an illustrative subset of Form 1040: text, currency, date, a comb (SSN), checkbox, radio-groups (including a boolean-valued one), and a repeated dependent block modeled as independent, explicitly-indexed field groups rather than a repeat construct. |
| [`examples/sample-data.json`](examples/sample-data.json) | The nested data set the example annotation binds against. |

Scope, by design: every value a field prints already exists in the caller's data set —
this spec positions, formats, and references values, but never computes or derives
them, and has no generic "repeat this row" construct. See SPEC.md section 1 for why.

## Quick overview

Positioning is in PDF points from the page's **top-left** corner (SPEC section 3). A
wages line is one field, pointing straight at a value the caller already computed:

```json
{ "id": "line-1a-wages", "type": "currency", "page": 1,
  "rect": { "x": 500, "y": 330, "w": 76, "h": 14 },
  "binding": "$.income.wages.total", "required": true }
```

* **`binding`** reaches into the caller's nested data with a tiny JSONPath subset:
  `$.taxpayer.ssn`, `$.dependents[1].relationship` (SPEC section 6).
* **`type`** selects formatting + layout behavior: `text`, `number`, `currency` (IRS
  whole-dollar rounding, `(1,234)` negatives), `date`, `comb` (one character per box,
  for SSNs/EINs), `checkbox`, and `radio-group` (mutually exclusive boxes, e.g. filing
  status or a Yes/No question). See SPEC section 5.
* A form's repeated slots (e.g. up to four dependents) are annotated as that many
  independent field groups, each bound to an explicit array index — no separate
  repeat/table concept to learn (SPEC section 6.4).

Validate an annotation document against the schema with any draft 2020-12 validator,
e.g.:

```bash
npx ajv-cli@5 validate --spec=draft2020 \
  -s schema/annotation.schema.json -d examples/f1040-simplified.annotation.json
```

# Important Links

### Calculating x,y coordinates of fields on pdf forms
https://jol333.github.io/pdf-coordinates/

### Exporting annotations from forms that are already annotated
https://online.sumatrapdfreader.org/exportpdfannotations
