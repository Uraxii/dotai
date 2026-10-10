---
name: write-tests
description: "Load whenever you write or change code. Run the existing suite first, then ship tests for new or changed behavior in the same commits, test-first when a test path is cheap. Bug fixes go through the tdd skill."
---

# Write tests

Code you write or change ships with tests that fail if its behavior breaks. This applies to every writer on every playbook.

## Before the work

1. Run the project's existing test suite and note the result. If a bead ordered the work, record the tests that already fail: `bd comment <id> "baseline failures at <SHA>: <test names>"`.
2. Fix each test that is stale against the current code before you change anything, and commit that fix on its own. A test that fails because of a real defect is not stale. Report it instead of editing it. A test the bead's tester committed is never stale. Follow Fix a failed round in the beads work loop for it.

## During the work

Steps 3 to 5 are for writers. A tester writes no production code and skips them.

3. For a bug fix, follow the **tdd** skill, so the failing test lands before the fix.
4. For new or changed behavior, write the test first when a test path is cheap. Use the closest unit, component, or integration test the codebase already uses for that path. Run it, confirm it fails for the reason you expect, then write the code.
5. When test-first is not practical, write the tests with the code, in the same commits.
6. Write each test per the **principle-test-behavior-not-implementation** principle skill.

## When a test is impractical

Do not skip silently. A test is impractical when it needs broad harness setup, brittle mocks, slow end-to-end infrastructure, or production-only state. Say why in the commit body, and run the closest executable check instead, such as a targeted script, a scenario run, or a type check. No new test is better than a bad test.

## Before you finish

7. Run the tests. Investigate unexpected failures. Decide if failures are real breaks or stale tests.
   - Tester: record a real break as `tests fail`. The developer fixes it.
   - Developer: fix the code for a real break. Update a stale test and give the reason in the commit body. A test the tester committed follows Fix a failed round instead.

No existing test is weakened or deleted without a reason in the commit body.

8. Name the tests you added and the suite result in your close reason or final message.
