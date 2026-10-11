# Production checks

A gate is a production check by an independent agent.
A skeptic reviews the work. A dedicated tester checks production code after the skeptic diff pass.
Work is for production when a PR will carry its commits. That work passes its gates before it ships.
Prototype, Investigation, Eval, and plan runs have no production gate. An interrogate panel is not a gate.
A required production gate has no `skip:`.

| Gate | Reviews | Runs | Fixer |
| --- | --- | --- | --- |
| Sketch review | The committed architect sketch and rationale | After synthesis, before implementation | The design agent |
| Diff review | The writer's base-to-head diff, including tests | After the writer reports its committed head | The writer, or a fresh writer with consolidated scope |
| Test gate | Test quality, missing coverage, and all applicable tests | After the skeptic diff pass for production code | Tester for test defects, writer for production defects |

Sketches and prose-only changes need no test gate. Writers choose whether to add tests.
Production code needs current skeptic and tester passes before runtime verification and shipping.
The tdd skill is the bug-test workflow. It does not replace the dedicated tester.

Use [Run records](../../ticket-work/references/run-records.md) for claims and run steps.
Use [Text files](../../ticket-work/references/text-files.md) for descriptions and verdict files.
Use [Shipping step 3](../playbooks/shipping.md) as the sole definition of patch equivalence.

## Own the skeptic review

1. For a sketch, commit the sketch and rationale before the review assignment.
   Before the spawn, create a gate bead under the bead that holds the work.
   Put the base SHA, scope, and done-when in its description.

   ```sh
   bd create "skeptic review: <sketch|diff> of <subject>" -t chore --parent <bead> --body-file <file> --silent
   ```

2. Spawn a fresh agent with the configured skeptic review model.
   Apply [Models in poteto-mode](../SKILL.md#models), including overrides and fallback.
   Its exact prompt is `Review bead <gate> at <SHA> in <worktree>.` Its actor is `skeptic-<gate>`.
   Give it [Review records](../../ticket-work/references/review-records.md) for the assignment.
3. On `verdict fail`, give the fixer its consolidated brief and `Fix bead <gate> at <SHA> in <worktree>.`
   The fixer follows [Fix rounds](../../ticket-work/references/fix-rounds.md).
   After the fixer reports a new head, spawn a fresh reviewer with the same prompt form at that head.
4. A gate takes at most three `verdict fail` comments.
   After the third, leave the gate open. Stop dependent work and report the open must-fix items to the user.
   Independent work can continue.
5. After `verdict pass at <SHA>`, check the receipts with `bd comments <gate> --json`.
   Check all these facts before closure:

   - The pass is the last verdict on the gate.
   - Its author wrote none of the work.
   - The reviewer marks each item from the last failed review and any linked test failure `fixed` or `answered`.
   - For a diff review, the pass covers the current patch under Shipping step 3.

   Close the gate with `bd close <gate> --reason "pass at <SHA>"`.
   Do not review a passed diff again unless a receipt check fails.

## Own the test gate

1. After the skeptic diff pass, create a `chore` test gate under the same parent as the diff gate.
   Do not create it under the closed diff gate.
   Put the base SHA, scope, done-when, suite commands, and allowed test paths in its description.
   Name the preceding diff gate and its pass SHA.

   ```sh
   bd create "test gate: <subject>" -t chore --parent <bead> --body-file <file> --silent
   ```

2. Pause the writer while the tester runs. Give the tester exclusive write access to the allowed test paths.
   Spawn a fresh agent with the configured test model per [Models in poteto-mode](../SKILL.md#models).
   Its exact prompt is `Test bead <gate> at <SHA> in <worktree>.` Its actor is `tester-<gate>`.
   The tester must have written none of the production code.
   Give it [Test records](../../ticket-work/references/test-records.md) for the assignment.
3. On `tests fail`, give the writer its consolidated brief, the findings, and `Fix bead <gate> at <SHA> in <worktree>.`
   Use [Fix rounds](../../ticket-work/references/fix-rounds.md). Keep the same unit and test gate for retries.
   After the writer reports a new head, obtain a fresh skeptic diff pass. Then spawn a fresh tester.
   A test gate takes at most three `tests fail` comments.
   After the third, leave the gate open. Stop dependent work and report the remaining failures and blockers.
   Independent work can continue.
4. Before the fresh skeptic spawn, name the linked test gate in the diff gate's description.
   Include the latest test failure and the writer's answers, especially disputed test contracts.
   Require the reviewer to assess each item against the preserved tester assertions.
   An unresolved contract dispute blocks the skeptic pass.
   If the reviewer confirms a wrong test contract, give that finding to the next tester to correct the test.
5. When the tester returns test commits, request a final skeptic review of the patch that includes those commits.
   If the review changes nothing, retain the tester's suite results.
   If the review requests a change, repeat the applicable gates at the new head.
   A production fix invalidates both passes. A changed assertion needs fresh review and test evidence.
   Build equivalence cannot prove assertion quality. For a pure restack, apply Shipping step 3.
6. Before closure, read `bd comments <gate> --json`.
   Check that the last test verdict passes at the final committed SHA.
   Check that its author wrote no production code and that each prior failed item is fixed or answered.
   Check that the test pass covers the final patch.
   Also check a current skeptic pass that includes every tester edit.
   Close the test gate with `bd close <gate> --reason "pass at <SHA>"`.

## Return the evidence

A delegate reports both gate IDs and the final SHA. Its spawner checks valid receipts instead of repeating gates.
An agent that cannot spawn returns its head and pending gates to its spawner.
If the brief assigns diff review and testing to the spawner, the worker runs only its sketch review.
Orchestrate, Autopilot-full, Autopilot-stack, and Shipping own diff and test gates for their workers and owners.
Runtime verification follows the required current passes.
