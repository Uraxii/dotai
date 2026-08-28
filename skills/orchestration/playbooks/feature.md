# Feature

Pick when: new or changed behaviour, built outward from a named data shape.
Structure-only change goes to Refactoring; defect goes to Bug fix.

Copy these steps into todolist verbatim before any task-specific todo.

1. **Clarify acceptance criteria BEFORE building.** Requirements ambiguous ->
   subagent loads `requirements-clarifier` first. Write criteria down, check them
   at end. Never build then ask what was wanted. Tracked work -> record in bd
   via `agent-workbench`.
2. **Name the data shape first.** Load `principle-foundational-thinking`. Before any
   logic: what is stored, what keys it, who owns it. Data-shape change late is a rewrite, early it is a one-line diff.
3. **Model state in types, not booleans.** Invalid states unconstructable. Two
   booleans that cannot both be true are one enum. Parse at boundary, do not
   validate at every use.
4. **Design shape before bodies.** `codebase-design` for seams, subagent loads
   `architect-designer` for skeleton: types, signatures, contracts, stub
   bodies. Question you cannot answer on paper -> `prototype`, then bin it.
   Design space genuinely open -> `principle-exhaust-the-design-space`.
   Skip stays as `architect skipped: <reason>`; never fold design silently
   into implementation.
5. **Scaffold before feature.** Anything every later phase needs goes first, in
   its own unit: schema, config, wiring, test harness. Nothing built twice.
6. **Break into units each ending in a check.** Verify each before starting
   next. Never batch edits and verify once. Disjoint files parallelize; shared
   writes serialize. One subagent best -> name why.
7. **Write.** Subagent loads `ponytail`, mandatory on any step writing code, and
   `code-quality` plus its reference for the language in play, both before
   first line. Add `principle-laziness-protocol` when the diff starts growing layers.
   Review the diff yourself; never pass through the delegate's summary.
8. **Prove on real artifact.** Load `principle-prove-it-works`. Run feature the way a
   user hits it. "It compiles" is not evidence behaviour exists.
9. **GATE.** Subagent loads `skeptic-gate`, serial: one gate, wait, fix, one
   fresh gate. Record verdict, head SHA, resolution as a `show-me-your-work` verdict row. Non-PASS
   halts delivery. Then `yeet`.

**Reply:** data shape chosen and why, acceptance criteria and which are met,
units and their checks, real-artifact evidence, gate verdict with SHA, open
decisions.
