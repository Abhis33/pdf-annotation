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
