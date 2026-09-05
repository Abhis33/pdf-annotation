# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

---

# Project-specific guidance: pdf-annotation

## What this project is

A specification (and JSON Schema) for annotating fields/boxes on U.S. tax forms, so
that an application — using its own proprietary code — can print values from a
caller's nested data set into exactly the right boxes on a form PDF. The annotation
document is the entire contract between the person who measures a form, the engineer
who builds a renderer, and the caller who supplies data.

## Key files

| Path | Role |
|------|------|
| `SPEC.md` | Normative specification: coordinate system, field types, formatting rules, the data-binding grammar, the rendering contract. Read this before changing the schema. |
| `schema/annotation.schema.json` | JSON Schema (draft 2020-12) that validates annotation documents. Must stay in sync with SPEC.md — a property that exists in one but not the other is a bug. |
| `examples/f1040-simplified.annotation.json` | Worked example exercising every field type. Must always validate against `schema/annotation.schema.json`. |
| `examples/sample-data.json` | The nested data set the example annotation binds against. |
| `README.md` | Entry point / quick overview, links into the above. |

## Design constraints (intentional, not gaps)

These were decided deliberately after discussion, not overlooked — do not "fix" them
without the user explicitly asking to expand scope:

1. **No computed/derived values.** Every value a field prints must already exist in
   the caller's data set. The schema has no transform/expression pipeline (no `sum`,
   `concat`, etc.). If a box needs "total wages across all W-2s," that total is
   expected to already be a field in the data set — the caller computes it upstream.
2. **No repeating/table field type.** A form's fixed number of repeated slots
   (e.g. up to four dependents) is annotated as that many independent field groups,
   each bound to an explicit array index (`$.dependents[0].name`,
   `$.dependents[1].name`, …), not via a generic repeat/offset construct. See
   SPEC.md section 6.4 for the full rationale and consequences.
3. **Binding grammar is intentionally tiny.** `$`-rooted dot/index paths only — no
   wildcards, filters, or descendant search. Every binding must name exactly one
   value.
4. **Fail loud, not silent, on money.** Missing required data, unknown field types,
   comb values of the wrong length, and text that can't fit even at `minFontSize` are
   all errors, never silently dropped or guessed at.

## Working conventions

- When you change `schema/annotation.schema.json`, update `SPEC.md` to match (and
  vice versa) — they are meant to describe the same contract in two forms (machine
  vs. prose).
- Validate any schema or example change:
  ```bash
  npx ajv-cli@5 validate --spec=draft2020 \
    -s schema/annotation.schema.json -d examples/f1040-simplified.annotation.json
  ```
- Field `id`s should mirror the form's printed labels (`line-1a-wages`,
  `dependent1-name`) so an annotation is reviewable against the paper form.
- Annotation files are named `<form.id>.annotation.json`, one per `(form.id,
  form.revision)` pair.
- Don't add new field types, transforms, or a repeat construct without confirming
  scope first — see "Design constraints" above.

## See also

`progress.md` for a log of what's been done in this repo and why.
