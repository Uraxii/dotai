---
name: tdd
description: Test-driven development. Use when the user wants to build features or fix bugs test-first, mentions "red-green-refactor", or wants integration tests.
---

# Test-Driven Development

Every section applies on every cycle. Consult them before and during the loop, not after.

Read the project's instructions file and any glossary or decision notes for the area you're touching, when they exist, so test names and interface vocabulary match the project's domain language.

## What a good test is

Tests verify behavior through public interfaces, not implementation details. Code can change entirely; tests shouldn't. A good test reads like a specification. "user can checkout with valid cart" tells you exactly what capability exists. And survives refactors because it doesn't care about internal structure.

See [tests.md](tests.md) for examples and [mocking.md](mocking.md) for mocking guidelines.

## Seams. Where tests go

A **seam** is the public boundary you test at: the interface where you observe behavior without reaching inside. Tests live at seams, never against internals.

**Test only at pre-agreed seams.** Before writing any test, write down the seams under test and confirm them with the user. No test is written at an unconfirmed seam. You can't test everything. Agreeing the seams up front is how testing effort lands on the critical paths and complex logic instead of every edge case.

Ask: "What's the public interface, and which seams should we test?"

## Anti-patterns

- **Implementation-coupled.** Mocks internal collaborators, tests private methods, or verifies through a side channel (querying the database instead of using the interface). The tell: the test breaks when you refactor but behavior hasn't changed.
- **Tautological.** The assertion recomputes the expected value the way the code does (`expect(add(a, b)).toBe(a + b)`, a snapshot derived by hand the same way, a constant asserted equal to itself), so it passes by construction and can never disagree with the code. Expected values must come from an independent source of truth: a known-good literal, a worked example, the spec.
- **Horizontal slicing.** Writing all tests first, then all implementation. Bulk tests verify _imagined_ behavior: you test the _shape_ of things rather than user-facing behavior, the tests go insensitive to real changes, and you commit to test structure before understanding the implementation. Work in **vertical slices** instead: one test, one implementation, repeat, each test a **tracer bullet** that responds to what the last cycle taught you.

## When a failing test is impractical

Do not silently skip the red step. Say WHY first (broad harness setup, brittle
mocks, slow end-to-end infra, production-only state, vague reproduction steps,
large unrelated fixture churn), then run the closest executable check instead:
targeted script, manual reproduction command, browser automation, snapshot
diff, log assertion, focused integration check. Report which one you used and
what it showed.

Prefer no new test over a bad test. Bad test = mostly tests mocks, encodes
current implementation details, depends on timing or unrelated global state,
needs expensive infrastructure for a small fix, or gets deleted right after
proving the fix.

## Rules of the loop

- **Red before green.** Write the failing test first, then only enough code to pass it. Don't anticipate future tests or add speculative features.
- **One slice at a time.** One seam, one test, one minimal implementation per cycle.
- **Refactoring is not part of the loop.** It belongs to the review stage (see the `code-quality` and `interrogate` skills), not the red → green implementation cycle.
