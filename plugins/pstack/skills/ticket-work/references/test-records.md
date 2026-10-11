# Run a tester gate

This reference executes one assignment with the prompt `Test bead <gate> at <SHA> in <worktree>.`

1. Set `BEADS_ACTOR=tester-<gate>` on each `bd` call.
   Create and claim your own run bead per [Run records](run-records.md#the-run-bead).
   Do not claim the writer's bead or the gate.
   Read the named gate, prior rounds, and passing skeptic gate.
   Confirm the input head and exclusive test-write scope before edits.
2. Read the full base-to-head diff, done-when, and all available tests.
   Identify absent coverage when the writer supplies no tests.
   Read [principle-test-behavior-not-implementation](../../principle-test-behavior-not-implementation/SKILL.md).
   Check meaningful assertions and real subject execution.
   Check errors, empty inputs, boundaries, and regressions relevant to the change.
   Derive incidental structure from actual state. Do not assume order or counts.
3. Design the missing cases. Choose unit, integration, or browser tests that fit the contract.
   Load required real fixtures. A missing fixture or test prerequisite is a blocker. Do not fabricate success.
4. Add or correct tests in the existing harness within the allowed paths. Edit no production code.
   Do not change a frozen parity or measurement baseline.
   Correct a proven stale writer test only with contract evidence and equivalent behavior coverage.
   Never remove a valid requirement to obtain green output.
   Commit test changes with a Conventional Commit subject. State the reason in the body.
5. Run all applicable tests, including new cases and adjacent regressions.
   Record each command, exit code, result, coverage gap, and environment blocker.
   A known failure still fails the all-tests-pass condition.
6. For a production defect, report the reproduction and failing assertion to the owner.
   Keep the failing test committed for the writer. Do not fix production code.
7. Write the verdict to a temporary file. Add it with `bd comment <gate> --file <file>`.
   Its first line is `tests pass at <final SHA>` or `tests fail at <final SHA>`.
   Use the actual committed head after tester edits.
   Name unresolved quality findings, missed coverage, and suite failures.
   Mark prior failed items fixed, answered, or still open.
8. Report the final head and test commits. Close your own step and run beads before return.
   The owner closes the gate.

A pass requires complete quality checks, required coverage, and successful suite execution.
A green count alone is insufficient.
An unavailable environment yields `tests fail` with a blocker description. It cannot count as a pass.
