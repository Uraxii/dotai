---
name: write-tests
description: "Load whenever you write or change code. Run the existing suite first, ship tests for new or changed behavior in the same commits, cover the negative cases, and fix stale tests after a structural change. Bug fixes go through the tdd skill."
---

# Write tests

Code that you write or change ships with tests that fail when its behavior breaks. This applies to every writer on every playbook.

## Before the work

1. Make sure that you can run the code and its tests. If no runtime or test runner exists, stop and report it. Do not skip the tests.
2. Run the existing suite and record the result. Fix each test that is stale against the current code before you change anything, and commit that fix separately. A test that fails because of a real defect is not stale. Report it. Do not edit it.

## During the work

3. For a bug fix, follow the **tdd** skill, so that the failing test lands before the fix.
4. For new or changed behavior, write the test first when a test path is cheap. Use the closest unit, component, or integration test that the codebase already uses for that path. Make sure that it fails for the reason you expect, then write the code. When test-first is not practical, write the tests with the code, in the same commits.
5. Write each test per **principle-test-behavior-not-implementation**. In addition:
   - Test the negative cases: invalid input, denied access, empty and boundary values, and failure paths. Test the boundary itself (for example 2 and 3 for a limit of 3), not many values on the same branch.
   - Derive structure from state. Do not hard-code counts, field names, or orders that the code does not promise.
   - Load the real data files that the code reads. Fail the test when a file is missing.
   - Exercise logic through the entry point that the application uses, not through a simulated click or a private helper.
   - Do not assert values that the test itself built, such as a mock's call arguments that the test wrote inline. Do not assert literals that only repeat the source, such as a CSS class string.

## When a test is impractical

Do not skip silently. A test is impractical when it needs a broad harness, brittle mocks, slow end-to-end infrastructure, or production-only state. Give the reason in the commit body, and run the closest executable check instead, for example a script, a scenario run, or a type check. No new test is better than a bad test.

## Before you finish

6. After a structural change (a component added or removed, a key renamed, a dependency added, a changed state shape), run the full suite and fix the stale tests. A stale test that passes is worse than a test that fails.
7. Run the tests and examine each unexpected failure. Fix the code for a real break. Update a stale test and give the reason in the commit body. Do not weaken or delete an existing test without a reason in the commit body.
8. Run the code in its real environment. Passing tests do not prove that the code is correct.
9. In your final message, name the tests that you added and the suite result.
