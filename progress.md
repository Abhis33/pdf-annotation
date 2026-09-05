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
  dev-tooling directories) and ran it once over the repo's
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

- Positive/negative fixture tests exercising the schema's actual validation
  rules (field-type discrimination, binding pattern edges, enum/format edges).
- An automated check that `examples/*.annotation.json` still validates against
  the schema (currently only done ad hoc / manually).
- Markdown link-checking for the relative links in SPEC.md/README.md/CLAUDE.md.
