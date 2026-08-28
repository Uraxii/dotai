---
name: tdd
description: Test-driven development. Use when the user wants to build features or fix bugs test-first, mentions "red-green-refactor", or wants integration tests.
---

# Test-driven development

## Rules of the loop

- **Red before green.** Write the failing test first, run it, confirm it fails
  for the intended reason, then write only enough code to pass it. Do not
  anticipate future tests or add speculative features.
- **One slice at a time.** One seam, one test, one minimal implementation per
  cycle. Never all tests then all implementation: bulk tests verify *imagined*
  behaviour, go insensitive to real changes, and lock in test structure before
  the implementation is understood. Each test is a tracer bullet that responds
  to what the last cycle taught.
- **Refactoring is not part of the loop.** It belongs to review
  (`principle-code-quality` and `interrogate` skills), not the red-green cycle.
- Do not change a test to match a wrong implementation, and do not weaken an
  assertion unless the expected behaviour genuinely changed.

## What a good test is

Verifies behaviour through the public interface, never implementation details.
The code can change entirely and the test should not. It reads like a
specification: "user can checkout with valid cart" names the capability. Test
names and interface vocabulary follow the project's domain language.

Expected values come from an independent source of truth: a known-good literal,
a worked example, the spec.

## Seams. Where tests go

A **seam** is the public boundary you test at, the interface where behaviour is
observed without reaching inside. Tests live at seams, never against internals.

**Test only at pre-agreed seams.** Before writing any test, write down the
seams under test and confirm them with the user. No test at an unconfirmed
seam. You cannot test everything; agreeing the seams up front is how effort
lands on critical paths instead of every edge case.

Mock at system boundaries only: external APIs, time, randomness, sometimes the
database or filesystem. Never mock your own modules or internal collaborators.

## Anti-patterns

- **Implementation-coupled.** Mocks internal collaborators, tests private
  methods, or verifies through a side channel (querying the database instead of
  using the interface). Tell: the test breaks on refactor with no behaviour
  change.
- **Tautological.** The assertion recomputes the expected value the way the
  code does (`expect(add(a, b)).toBe(a + b)`, a hand-derived snapshot), so it
  passes by construction and can never disagree with the code.

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
