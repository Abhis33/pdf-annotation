# Progress log

## 2026-09-05 — Initial specification, schema review, and worked example

**Starting point:** an empty repo (`LICENSE` + a two-line `README.md`) plus a draft
`schema/annotation.schema.json` at the repo root that was not yet documented or
exercised against an example.

**Decisions made** (via clarifying questions before any implementation):

1. `schema/annotation.schema.json` is the authoritative direction — kept
   intentionally simpler than earlier exploration: annotation-only, no business
   logic.
2. **No computed/derived values.** Every printed value must already exist in the
   caller's data set; the spec has no transform/expression pipeline. Aggregation
   (e.g. totaling wages across multiple W-2s) is the caller's responsibility before
   the data reaches a renderer.
3. **No repeating/table field type.** Repeated form slots (e.g. dependents) are
   annotated as independent, explicitly-indexed field groups
   (`$.dependents[0].*`, `$.dependents[1].*`, …) rather than a generic repeat
   construct.
4. Deliverable scope: the schema itself, a written spec (`SPEC.md`), and one worked
   example (annotation + sample data) — no reference renderer this round.
5. File layout: edit `schema/annotation.schema.json` in place; add `SPEC.md` and
   `examples/` at the repo root.

**Work done:**

- Reviewed `schema/annotation.schema.json` and fixed one real issue: the `field`
  definition used `unevaluatedProperties: false` without a sibling
  `type: "object"`, which is undefined behavior under strict JSON Schema tooling
  (caught via `ajv-cli` strict-mode warning). Added the missing `type: "object"`.
  No other schema changes were needed — it already matched the no-transforms,
  no-table design.
- Wrote `SPEC.md`: the normative specification covering scope/non-goals, document
  model, coordinate system (top-left origin, point units, PDF-space conversion),
  style resolution, all seven field types (`text`, `number`, `currency`, `date`,
  `comb`, `checkbox`, `radio-group`) with their formatting options, the binding
  grammar and resolution/missing-value rules, the independent-field-group
  convention for repeated structures (with rationale and consequences), the
  rendering contract, and a conformance checklist.
- Created `examples/sample-data.json`: a nested taxpayer data set (taxpayer info,
  filing status, two dependents, income) with pre-computed totals (no aggregation
  expected of the renderer).
- Created `examples/f1040-simplified.annotation.json`: an illustrative subset of
  Form 1040 annotated against that data set, exercising every field type,
  including two dependents modeled as two independent four-field groups (name,
  SSN, relationship, CTC checkbox).
- Updated `README.md` to point at `SPEC.md`, the schema, and the examples, with a
  short quick-start and the validation command.
- Validated throughout with `npx ajv-cli@5 validate --spec=draft2020`: the schema
  compiles cleanly (no strict-mode warnings after the fix), and the worked example
  validates against it.
- Added `CLAUDE.md` and this `progress.md` to keep the design constraints and
  session history discoverable for future work.

**Status:** schema, spec, README, and worked example are consistent and validated.
Nothing has been committed to git yet.

**Open items / possible next steps** (not started, not committed to):

- A reference renderer implementation (resolve → validate → format → draw) was
  explicitly deferred this round.
- Field-level data validation (checksum/pattern rules on bindings) is out of scope
  for now.
- Conditional fields (`when` predicates) are out of scope for now.

## 2026-09-05 (later) — Test infrastructure and formatting

**Ask:** discussed what testing/linting/style tooling would make sense for a
JSON-Schema-plus-docs repo (see prior discussion in conversation, not recorded
here); decided to implement the highest-value, lowest-cost piece first (schema
validity/lint) plus a formatter, using Python as the primary language for new
tooling. Explicitly deferred: the positive/negative fixture test suite, an
automated example-vs-schema regression check, and Markdown link-checking.

**Work done:**

- Added `tests/test_schema_validity.py` (pytest + the `jsonschema` library):
  checks `schema/annotation.schema.json` is valid JSON, conforms to the JSON
  Schema draft 2020-12 meta-schema, and has no dangling internal `$ref`s. All
  three pass against the schema unchanged — no schema edits were needed.
- Added `pyproject.toml` (`[tool.pytest.ini_options]`, `[tool.black]`,
  `[tool.ruff]`) and `requirements-dev.txt` (pinned: `jsonschema`, `pytest`,
  `black`, `ruff`) for a reproducible Python dev setup.
- Added Prettier config (`.prettierrc.json`, `.prettierignore` — excludes
  `output/` and dev-tooling directories) and ran it once over the repo's
  existing JSON/Markdown files to establish a clean baseline. This reformatted
  `schema/annotation.schema.json`, `examples/f1040-simplified.annotation.json`,
  `README.md`, `SPEC.md`, and `CLAUDE.md` — confirmed semantically identical
  for the JSON files (byte-for-byte equal parsed objects) and re-validated the
  example against the schema afterward; the Markdown changes are Prettier's
  standard style normalization (bullet marker, emphasis marker, table padding),
  not wording changes.
- Updated `CLAUDE.md` with a "Development setup" section documenting how to
  install, test, format, and lint.
- Ran `pytest`, `black --check`, `ruff check`, and `prettier --check` together
  as a final pass; all clean.

**Status:** schema validity is now covered by an automated (Python) test, and
JSON/Markdown formatting is enforced by Prettier with Python code (currently
just the test file) formatted by black/ruff. Nothing has been committed to git
yet.

**Open items / possible next steps** (still not started):

- An automated check that `examples/*.annotation.json` still validates against
  the schema (currently only done ad hoc / manually).
- Markdown link-checking for the relative links in SPEC.md/README.md/CLAUDE.md.

## 2026-09-05 (later still) — A few core positive/negative fixture checks

**Ask:** add positive/negative fixture tests, but scoped down deliberately —
"a few core things," not full coverage of every field type/enum, and not a
fixtures directory with one file per case. Agreed plan before implementing:
one new test file, fixtures as inline Python dicts (a single minimal valid
base document, deep-copied and mutated per case), four total test functions.

**Work done:**

- Added `tests/test_annotation_validation.py`: one positive test (a minimal
  valid document — `specVersion`, `form`, one page, one `text` field —
  validates) plus three negative tests, each the base document with one
  targeted mutation:
  - a required top-level key (`fields`) removed,
  - a field's `binding` missing the `$` root (`"taxpayer.ssn"` instead of
    `"$.taxpayer.ssn"`),
  - a field with an unrecognized property added (`bogus: true`) — a direct
    regression guard for the `unevaluatedProperties`/`type: object` fix made
    in the first testing pass.
- All 4 new tests pass alongside the existing 3 schema-validity tests (7
  total); running them confirmed the schema actually rejects all three
  mutations, not just that the positive case happens to pass.
- Formatted/linted with `black`/`ruff` (clean, no changes needed).
- Updated `CLAUDE.md`'s "Key files"/"Development setup" sections to describe
  the new test module and removed the now-stale "positive/negative fixture
  tests" line from the open-items list above.

**Status:** two test modules now exist —
`tests/test_schema_validity.py` (the schema is well-formed) and
`tests/test_annotation_validation.py` (a handful of core validation rules
actually hold). Deliberately still not covering every field type, enum, or
format option. Nothing committed to git yet.

## 2026-09-05 (later still) — Reference renderer implementation

**Ask:** build the reference renderer previously deferred: `python main.py
<annotation.json> <input_data.json> <input_pdf>` produces `output/output.pdf`,
plus a log file under `logs/` capturing anything that went wrong during the run.

**Also found and fixed in passing:** `CLAUDE.md`, `README.md`, `progress.md`, and
`.prettierignore` had leftover unresolved `<<<<<<<`/`=======`/`>>>>>>>` git conflict
markers (from an earlier `git stash` conflict that was never cleaned up) sitting in
the tracked file content. Resolved all four in favor of the newer ("Stashed
changes") side, which was a strict superset of the older side in every case — no
content was lost.

**Work done:**

- Added `requirements.txt` (runtime deps, separate from `requirements-dev.txt`):
  `jsonschema` (already a dev dep, now also runtime), `reportlab` (drawing),
  `pypdf` (reading/writing the source PDF).
- Added the `annotator/` package implementing the SPEC.md rendering contract:
  - `binding.py`: section 6 path resolution (`$.a.b[0].c`) and the strict,
    type-sensitive equality used by `checkedWhen`/radio-group option matching
    (so `1 != "1"` and `True != 1`, per 5.6/5.7).
  - `formatting.py`: section 7.1 number/currency formatting (half-away-from-zero
    rounding via `Decimal`, thousands separator, minus/parentheses negatives,
    print/blank/dash zero handling), date token substitution, and comb-value
    character stripping/length validation.
  - `styles.py`: section 4 per-property style resolution (field -> defaults ->
    spec default) and family/weight -> base-14 PDF font name mapping (unknown
    families fall back to Helvetica with a logged warning, per spec).
  - `render.py`: section 3 coordinate conversion, section 7.2 layout (single-line
    alignment via font ascent/descent metrics, greedy word-wrap for
    `multiline`), section 7.3 overflow (`shrink`/`truncate`/`error`), and drawing
    for all seven field types. Renders one reportlab overlay page per source PDF
    page, then merges it onto the original via `pypdf` so the source form's own
    content is preserved.
  - Field-level errors are collected across the whole document (not
    fail-fast-on-first) so a run reports every failing field at once.
- Added `main.py`: CLI entry point. Validates the annotation document against
  `schema/annotation.schema.json` before doing anything else; writes a
  timestamped log file per run to `logs/` (so concurrent/repeated runs don't
  clobber each other) with warnings mirrored to stderr; exits non-zero without
  writing `output.pdf` if schema validation or any field's render fails.
- Checkmark mark (`mark: "check"`) is drawn as two vector line strokes rather
  than a ZapfDingbats glyph — found via manual visual testing that at least one
  common PDF rasterizer substitutes a filled "missing glyph" box for that font/
  character code instead of an actual check mark. Vector strokes render
  correctly everywhere and avoid the dependency entirely.
- Manually verified end-to-end against `examples/` (runs cleanly, no warnings,
  page dimensions match) and against ad hoc fixtures built to exercise: all
  three checkbox marks, an unchecked box, radio-group selection, multiline
  word-wrap, overflow `shrink`, negative currency parentheses-rounding, and comb
  digit placement — by rendering output PDFs to PNG and inspecting them.
  Also verified the three failure paths (missing required value, schema-invalid
  annotation document, missing source PDF) each exit non-zero with a clear
  console message and a log file naming the specific problem.
- All 7 existing tests (`pytest`) still pass, unmodified. `black`/`ruff` clean
  on `main.py` and `annotator/`.

**Status:** a working reference renderer exists end-to-end for all seven field
types. Nothing has been committed to git yet.

**Open items / possible next steps** (not started, not committed to):

- `sourcePdf.sha256` (SPEC.md section 2) is not checked by the renderer — it's
  documented as a pin against the wrong PDF revision but nothing currently
  verifies it.
- Font embedding is not supported — `styles.py` only maps onto the PDF standard
  14 fonts (Helvetica/Times/Courier families); a `font.family` outside those
  falls back to Helvetica with a warning rather than embedding the requested
  font.

## 2026-09-05 (later still) — Automated tests for `annotator/`

**Ask:** close the "no automated tests for `annotator/`" gap noted above.

**Work done:**

- Added `pythonpath = ["."]` to `[tool.pytest.ini_options]` in `pyproject.toml`
  — without it, `annotator` isn't importable from `tests/` (no
  `tests/__init__.py`, and pytest's default "prepend" import mode only puts
  `tests/` itself on `sys.path`, not the repo root).
- `tests/test_binding.py` (12 tests): path resolution rules from SPEC.md
  6.1/6.2/6.3 (member/index access, missing vs. `null`, non-object/non-array
  access, falsy-but-present values) and the `strict_equals` gotchas the spec
  calls out by name (`1 != "1"`, `True != 1`).
- `tests/test_formatting.py` (20 tests): half-away-from-zero rounding for both
  signs, both `negativeFormat`s, all three `zeroFormat`s, thousands separator,
  currency symbol, decimal places, date token substitution (including the
  `YYYY` vs. `YY` ambiguity), and comb stripping/length validation for both
  `fit` modes.
- `tests/test_styles.py` (7 tests): per-property resolution order (field ->
  defaults -> spec default), confirming a partial `font` override doesn't
  drop sibling properties, and the font-family fallback-with-warning path.
- `tests/test_render.py` (6 tests): end-to-end smoke tests against small
  synthetic PDFs built in-memory with reportlab (not `examples/f1040.pdf`, to
  keep these fast and independent of that fixture) — a successful text
  render (verified via `pypdf`'s `extract_text()`), a checkbox `X` mark, a
  page-size-mismatch warning, and the three error paths (required-missing,
  `overflow: "error"`) including that a failed render never writes the output
  file and that the combined `RenderError.all_errors` names the right field.
- All 45 new tests passed on the first run; existing 7 tests unaffected.
  `black`/`ruff` clean on `tests/`.

**Status:** all four `annotator/` modules now have automated coverage — the
three pure-function modules at the unit level, `render.py` via targeted
end-to-end smoke tests. 52 tests total. The `sourcePdf.sha256` and font
embedding items above remain open.
