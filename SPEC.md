# Tax Form Annotation Specification

**specVersion 1.0**

This document is the normative specification for annotating fields and boxes on U.S. tax
forms. An *annotation document* describes, for one revision of one form, where every
fillable box sits on the page, how the value printed inside it must be formatted, and
which single value from a caller's own (arbitrarily nested) data set belongs there.
Given an annotation document, a data set, and the blank form PDF, an application with no
built-in knowledge of that specific form can print a completed return.

Machine-validatable structure: [`schema/annotation.schema.json`](schema/annotation.schema.json)
(JSON Schema, draft 2020-12). A complete worked example is in
[`examples/`](examples/): [`f1040-simplified.annotation.json`](examples/f1040-simplified.annotation.json)
annotates an illustrative subset of Form 1040 against
[`sample-data.json`](examples/sample-data.json).

The key words MUST, MUST NOT, SHOULD, and MAY are to be interpreted as in RFC 2119.

---

## 1. Scope

**What this spec is:** a description of *where* a value goes, *how* it must look once
printed, and *which* value in the caller's data set it comes from.

**What this spec is deliberately not:** a place to compute or derive values. Every value
a field prints MUST already exist, in its final printed form's underlying value, somewhere
in the caller's data set. If a box needs "total wages across all W-2s," the caller
computes that total and puts it in the data set (e.g. `income.wages.total`); the
annotation only points at it. This keeps the annotation format auditable by a
non-engineer (a tax reviewer can read a binding path and know exactly what prints, with
no hidden arithmetic to trace) and keeps all business/tax logic where it belongs — in the
caller's proprietary code, not duplicated inside every renderer that consumes this format.

The same reasoning excludes a generic "repeating row" construct. A form with a
fixed number of repeated slots (dependents, additional payers, etc.) is annotated as
that many **independent field sets**, each explicitly bound to one array index — see
section 6.4. This costs a few more lines of JSON per form but means every field is
self-contained: there is no separate repeat/offset mechanism to learn, and the
document a tax reviewer looks at literally shows one entry per printed box, matching
the paper form line for line.

Two consequences worth stating up front:

* A field can be **skipped** (nothing printed) when its bound value is absent — see
  section 6.3 — but it can never be **conditionally rendered** based on some other
  field's value, and it can never **transform** its input. Both are intentionally out
  of scope for this version.
* Because there's no derived/aggregate value support, "the fifth dependent doesn't
  fit" is not a case this spec detects. If a form only defines two dependent field sets
  and the data set has three dependents, the third is simply never referenced by any
  binding — the caller is responsible for deciding what to do with data it knows won't
  fit the boxes it has (e.g., producing an attachment) before invoking a renderer.

## 2. Document model

An annotation document is a single JSON object:

| Property      | Req | Meaning |
|---------------|-----|---------|
| `specVersion` | ✓   | Always `"1.0"` for this spec. Renderers MUST reject other values. |
| `form`        | ✓   | Identity: `id` (e.g. `"f1040"`), `revision` (e.g. `"2025"`), optional `name`, `taxYear`, `jurisdiction`, `sourcePdf`. |
| `pages`       | ✓   | One entry per annotated page; establishes the coordinate space (section 3). |
| `defaults`    |     | Document-wide style defaults (section 4). |
| `fields`      | ✓   | The annotated boxes (section 5). |

**Form identity.** Coordinates are only meaningful against one printing of one form. The
pair (`form.id`, `form.revision`) MUST uniquely identify the annotation; the IRS moves
boxes between years, so the 2025 and 2026 Form 1040 are two separate annotation documents.
`sourcePdf.filename` SHOULD name the exact blank PDF the coordinates were measured
against; its optional `sha256` pins the exact byte content, so a renderer (or CI) can
detect when someone points an old annotation at a revised PDF.

## 3. Coordinate system

* **Unit:** PDF points, 1 pt = 1/72 inch (`page.unit` is always `"pt"`). US Letter is
  612 × 792 pt.
* **Origin:** the **top-left corner of the page** (`page.origin` is always `"top-left"`),
  x increasing rightward, y increasing **downward**.
* Every field names its `page` (1-based index into the source PDF).

The top-left origin is deliberate: humans and annotation tools measure forms from the
top of the page down, and screen/screenshot coordinates already work this way. PDF's
native coordinate system has a bottom-left origin with y increasing upward, so a renderer
drawing with a PDF library MUST convert:

```
pdf_x = x
pdf_y = page.height − y − h      # y of the rect's bottom edge, in PDF space
```

A **rect** `{x, y, w, h}` describes a box: `(x, y)` is its top-left corner, in the page's
own coordinate space. Rects SHOULD trace the printed box on the form; the renderer
handles insetting via `style.padding` (section 4).

## 4. Styles

Style properties may appear in `defaults` (document-wide) and in any field's `style`
(field-level). Resolution order for each individual property: **field → defaults → spec
default**, where the spec defaults are:

| Property                    | Default       | Meaning |
|------------------------------|---------------|---------|
| `font.family`                | `"Helvetica"` | Font family name. Renderers MUST substitute a metrically similar font if unavailable. |
| `font.size`                  | `9`           | Point size. |
| `font.weight`                | `"normal"`    | `normal` \| `bold`. |
| `font.color`                 | `"#000000"`   | `#rrggbb`. |
| `textAlignment`               | `"left"`      | Horizontal alignment within the padded rect: `left` \| `center` \| `right`. |
| `verticalAlignment`          | `"middle"`    | Vertical alignment within the padded rect: `top` \| `middle` \| `bottom`. |
| `padding.{left,right,top,bottom}` | `2` each | Inset in points applied to the corresponding rect edge before layout. |
| `overflow`                   | `"shrink"`    | See section 7.3. |
| `minFontSize`                | `5`           | Floor for `shrink`. |
| `lineHeight`                 | `1.15`        | Line-height multiplier for multiline text. |

Resolution is per-property, not per-object: a field's `style` may set only `font.size`
and still inherit every other property (including the rest of `font`) from `defaults`
or the spec default.

## 5. Field types

Every field, regardless of type, shares the base properties defined by `fieldBase` in
the schema: `id` (unique in the document; convention is the form's own printed line
label, e.g. `"line-1a"`, or a descriptive slug for boxes with no line number), `type`,
`page`, `binding` (section 6), `label` and `notes` (both documentation only, never
rendered), `formReference` (optional pointer to the printed `line`/`box`/`section`, for
reviewing the annotation against the paper form), `required`, `default`, and `style`.

**`required` / `default` semantics** (shared by every field type): if the binding
resolves to *missing* (section 6.3) — with `required: true`, rendering MUST fail with an
error naming the field `id`; otherwise, if `default` is present, that value is used as
if it had been the resolved value; otherwise the field is **skipped** (nothing is drawn —
the correct behavior for, e.g., an absent second dependent's SSN).

### 5.1 `text`

Free text in a `rect`. `multiline: true` enables word-wrapping (section 7.2);
`case: "upper"` uppercases the value; `maxLength` caps the character count, with excess
handled by the overflow policy (section 7.3).

```json
{ "id": "taxpayer-first-name", "type": "text", "page": 1,
  "rect": { "x": 36, "y": 104, "w": 200, "h": 16 },
  "binding": "$.taxpayer.firstName", "required": true }
```

### 5.2 `number`

A general numeric value (counts, percentages, years — anything that isn't a dollar
amount). `format` (all optional): `decimalPlaces` (default `0`), `thousandsSeparator`
(default `true`), `negativeFormat` (`"minus"` default, or `"parentheses"`), `zeroFormat`
(`"print"` default, `"blank"`, or `"dash"`). The bound value (after `required`/`default`
resolution) MUST be a JSON number; a numeric string is a data error, not something the
renderer silently coerces.

### 5.3 `currency`

A dollar amount. Same `format` shape as `number`, with defaults suited to IRS practice:

* `currency`: ISO 4217 code, default `"USD"`.
* `decimalPlaces`: `0` (default) or `2`. With `0`, the renderer MUST round **half away
  from zero** (the IRS "round half up" rule: 50¢ rounds to the next dollar, and
  −$1.50 rounds to −$2).
* `currencySymbol` (default `false`): leading currency symbol. IRS boxes pre-print the
  `$`, so leave this false unless annotating a form that doesn't.
* `negativeFormat` default `"parentheses"`, the IRS-preferred loss notation: `(1,234)`.

```json
{ "id": "line-1a-wages", "type": "currency", "page": 1,
  "rect": { "x": 500, "y": 330, "w": 76, "h": 14 },
  "binding": "$.income.wages.total", "required": true }
```

### 5.4 `date`

The bound value MUST be an ISO-8601 date string (`YYYY-MM-DD`). `dateFormat` (default
`"MM/DD/YYYY"`) is the output template; tokens `YYYY`, `YY`, `MM`, `DD` are replaced
(zero-padded), all other characters are printed literally. A form with separate
month/day/year boxes is annotated as three `date` fields, all bound to the same path,
with `dateFormat` set to `"MM"`, `"DD"`, and `"YYYY"` respectively.

### 5.5 `comb`

One character per printed box: SSNs, EINs, ZIP codes, routing numbers. Instead of a
single `rect`, a comb field gives:

* `cells`: number of boxes.
* `cellOrigin`: top-left corner of the **first** cell.
* `pitch`: distance between the left edges of adjacent cells.
* `cellSize`: `{w, h}` of each cell.
* `gaps` (optional): extra horizontal spacing after specific cells — SSN layouts leave a
  visual gap for the hyphens after cells 3 and 5.
* `fit` (default `"exact"`): after stripping the value to digits/letters, its length
  MUST equal `cells`; a mismatch is a render error (a 7-digit "SSN" must never print).
  `"left"`: length MUST be ≤ `cells`; the value fills from cell 1, remaining cells stay
  blank — the right behavior for bank account number boxes, which forms often
  over-provision.

Layout: cell *i* (1-based) has left edge
`x_i = cellOrigin.x + (i−1)·pitch + Σ(gap.extra for every gap with afterCell < i)`.
Each character is drawn centered in its cell, using the field's resolved style.

```json
{ "id": "taxpayer-ssn", "type": "comb", "page": 1,
  "binding": "$.taxpayer.ssn", "required": true,
  "cells": 9, "cellOrigin": { "x": 470, "y": 104 },
  "pitch": 13, "cellSize": { "w": 12, "h": 16 },
  "gaps": [ { "afterCell": 3, "extra": 6 }, { "afterCell": 5, "extra": 6 } ] }
```

The renderer MUST strip non-alphanumeric characters from the resolved value before
counting/placing cells, so `"123-45-6789"` and `"123456789"` annotate identically.

### 5.6 `checkbox`

A single box, marked or left empty, driven by one predicate over the bound value:
`checkedWhen: { "equals": v }` (strict, type-sensitive equality — `1` ≠ `"1"`) or
`checkedWhen: { "truthy": true }`. `mark` is `"X"` (default), `"check"` (✓), or
`"fill"` (a solid fill covering ~70% of the rect). An unchecked box prints nothing.

Prefer `radio-group` (5.7) over a pair of independent checkboxes whenever the boxes are
meant to be mutually exclusive (e.g. a Yes/No question): a radio-group *guarantees* at
most one mark is drawn, while two checkboxes are only exclusive if their predicates
happen to be complementary.

### 5.7 `radio-group`

One binding, several mutually exclusive boxes; the option whose `value` strictly equals
the resolved value is marked, every other option stays empty. Option values may be any
JSON scalar, including booleans — a Yes/No question is naturally a two-option
radio-group. If no option's value matches the resolved value: `required: true` is an
error, otherwise nothing is marked.

```json
{ "id": "filing-status", "type": "radio-group", "page": 1,
  "binding": "$.return.filingStatus", "required": true,
  "options": [
    { "value": "single", "rect": { "x": 40, "y": 78, "w": 9, "h": 9 }, "label": "Single" },
    { "value": "mfj", "rect": { "x": 88, "y": 78, "w": 9, "h": 9 }, "label": "Married filing jointly" }
  ] }
```

## 6. Data binding

### 6.1 Path grammar

A binding is a string conforming to (see the schema's `binding` pattern):

```
binding  = "$" segment*
segment  = "." name index?
name     = [A-Za-z_][A-Za-z0-9_]*
index    = "[" [0-9]+ "]"
```

`$` alone refers to the whole data set (rarely useful directly, but valid). Examples:

```
$.taxpayer.ssn
$.income.wages.total
$.dependents[0].name
$.dependents[1].qualifiesForCTC
```

This is intentionally a small subset of JSONPath: no descendant search (`..`), no
wildcards (`[*]`), no filters, no slices. Every binding names **exactly one** value —
there is never a question of what a box will print by reading its binding. Resolution
needs on the order of 15–20 lines of code in any language; no third-party JSONPath
engine is required. An annotator who needs "the second dependent's relationship" writes
`$.dependents[1].relationship`: an explicit index, zero ambiguity.

### 6.2 Resolution

Starting from the data set root, apply each segment in order: member access by `name`,
then, if present, element access by the zero-based `index`. Member access on a
non-object, index access on a non-array, an absent member, or an out-of-range index all
resolve to **missing** (not a resolution-time error — see 6.3). A resolved JSON `null`
is also treated as missing.

### 6.3 Missing values

Missing flows into the `required`/`default` rule stated in section 5: error if
`required`, else `default` if present, else skip the field. This three-way rule is the
*entire* error-handling model for absent data. Renderers MUST NOT invent additional
fallbacks (printing `"undefined"`, coercing `null` to `0`, etc.).

### 6.4 Modeling repeated entries: independent fields, not a repeat construct

Real forms have a fixed, small number of repeated slots — the 1040 prints up to four
dependents; Schedule B prints a fixed number of payer rows before pointing to a
continuation. This spec has no "repeat this field N times" construct. Instead, **the
annotator writes one field (or one small group of fields) per slot, each bound to an
explicit array index**, exactly as if the slots were independent named boxes on the
form — because, from the annotation's point of view, they are:

```json
{ "id": "dependent1-name", "type": "text", "page": 1,
  "rect": { "x": 36, "y": 250, "w": 150, "h": 14 },
  "binding": "$.dependents[0].name" },
{ "id": "dependent1-relationship", "type": "text", "page": 1,
  "rect": { "x": 320, "y": 250, "w": 110, "h": 14 },
  "binding": "$.dependents[0].relationship" },

{ "id": "dependent2-name", "type": "text", "page": 1,
  "rect": { "x": 36, "y": 266, "w": 150, "h": 14 },
  "binding": "$.dependents[1].name" },
{ "id": "dependent2-relationship", "type": "text", "page": 1,
  "rect": { "x": 320, "y": 266, "w": 110, "h": 14 },
  "binding": "$.dependents[1].relationship" }
```

(See [`examples/f1040-simplified.annotation.json`](examples/f1040-simplified.annotation.json)
for the full four-field group — name, SSN, relationship, and a CTC checkbox — repeated
for two dependents.)

Consequences of this choice, stated explicitly so they aren't mistaken for
oversights:

* The number of slots a form can print is fixed by however many field groups the
  annotator writes, once, when annotating the form — it is not computed from the data.
  This matches the paper form, which also has a fixed number of boxes.
* `required: false` on every field in a slot (the normal choice) means an unpopulated
  slot — `$.dependents[1]` absent because there's only one dependent — resolves every
  field in that group to missing, and every one of them is silently skipped. No special
  "empty slot" handling is needed; section 6.3's ordinary missing-value rule covers it.
* If the data set has *more* entries than the form has slots for, the extra entries are
  simply never referenced by any binding. This spec does not detect or report that
  case, by design (section 1): deciding what to do about overflow — e.g., preparing an
  IRS continuation/attachment statement — is business logic that belongs in the
  caller's own code, before it hands data to a renderer, not in the annotation format.
* This does mean an N-slot form's annotation is `N ×` as many field entries as a
  hypothetical repeat construct would need. That verbosity is the deliberate trade:
  every field stays a self-contained, independently reviewable box with exactly one
  binding, and the format has one less concept (no offset/repeat semantics) for an
  implementer to get wrong.

## 7. Rendering contract

Given (annotation document, data set, blank PDF), a conforming renderer MUST, for each
field, in order:

1. **Resolve** the binding (section 6.2).
2. **Apply** `required`/`default` (section 6.3); skip the field if it comes up missing
   and isn't required and has no default.
3. **Validate the type** expected by the field (`number`/`currency` → JSON number,
   `date` → ISO date string, `comb` → string, `checkbox`/`radio-group` → any JSON
   scalar).
4. **Format** to a string per the field type's rules (section 7.1); not applicable to
   checkbox/radio-group marks.
5. **Lay out and draw** within the padded rect (section 7.2), converting coordinates to
   the PDF library's native space (section 3).

Fields are independent; render order doesn't matter. Every error mandated by this spec
MUST identify the offending field's `id`.

### 7.1 Formatting

* **number/currency:** round to `decimalPlaces` (half away from zero), group thousands
  with `,` if `thousandsSeparator`, render the fraction with `.`. Negative values: wrap
  the whole rendered amount (symbol included) in parentheses for `"parentheses"`
  (`($1,234)`), or prefix with `-` for `"minus"`. Exact zero, per `zeroFormat`:
  `"print"` → `0` (or `0.00`), `"blank"` → skip the field, `"dash"` → an em dash.
* **date:** apply `dateFormat` tokens (section 5.4).
* **text:** apply `case`, then check `maxLength` (an overflowing `maxLength` follows the
  overflow policy below).

"Fits" (used below) means: the rendered string's width is ≤ `rect.w` minus left+right
padding, and its height is ≤ `rect.h` minus top+bottom padding, measured with the actual
metrics of the font the renderer selected.

### 7.2 Layout

Single-line text is placed in the padded rect per `textAlignment`/`verticalAlignment`.
Multiline text (`multiline: true`, `text` fields only) word-wraps greedily at spaces to
the padded width, with line spacing `font.size × lineHeight`; `verticalAlignment`
positions the resulting block within the padded rect.

### 7.3 Overflow

When the formatted text does not fit (7.1) at the field's effective font size:

* `"shrink"` (default): reduce the font size in small steps until it fits or
  `minFontSize` is reached; if it still doesn't fit at `minFontSize`, escalate to an
  error. This is the safe default for anything numeric: legibility degrades gracefully,
  and nothing is ever silently lost.
* `"truncate"`: cut characters from the end until it fits. The renderer MUST surface a
  warning naming the field. SHOULD be reserved for cosmetic, non-numeric fields (e.g. an
  occupation field) where losing trailing characters can't misstate a filed amount.
* `"error"`: fail immediately, no attempt to shrink or truncate. Use for any field where
  a partially-printed value would misstate what's being filed.

## 8. Conventions & versioning

* Field `id`s SHOULD mirror the form's printed labels (`line-1a-wages`,
  `dependent1-name`), so an annotation is reviewable side-by-side against the paper
  form.
* Annotation files SHOULD be named `<form.id>.annotation.json` and kept one per
  `form.revision`, since the IRS moves boxes between tax years.
* This spec is versioned by `specVersion`, independent of any one form's `revision`. A
  renderer encountering a `specVersion` it does not fully implement MUST refuse to
  render rather than guess — silently mis-printing a box is worse than refusing to run.

## 9. Conformance checklist

A renderer conforms if it: validates documents against
[`schema/annotation.schema.json`](schema/annotation.schema.json) (or an equivalent
check); implements the section 3 coordinate conversion; implements the full section 6.1
binding grammar and section 6.2 resolution algorithm; implements every section 5 field
type per the section 7 pipeline; and reports every MUST-level error together with the
offending field's `id`.
