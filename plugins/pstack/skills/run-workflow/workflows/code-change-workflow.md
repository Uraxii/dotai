# Code-change workflow

Use this saved workflow for authorized production code changes.
Read it before execution. Use it for each production-code unit in a custom run.
For a workflow-only handoff, return the selected steps and stop before execution.
A direct architecture request starts with requirements and stops at the requested design handoff.
Proposals, read-only investigations, plan runs, and throwaway prototypes keep their requested stop point.
Before a prototype becomes production work, start this workflow.

The owner runs each dependent phase only after it receives the required context.
The owner executes the planner's scope, priorities, and sequence. It does not replace the planner's product decisions or the architect's technical decisions.
Run independent tasks together only when they have separate output scopes.
Give concurrent writers separate worktrees or branches. Sequence edits to shared outputs.
Use [ticket-work](../../ticket-work/SKILL.md) for claims, steps, text-file arguments, and agents without database access.

## Requirements planning

Run requirements planning in both Full and Lightweight modes, before dependent design or implementation.
Give a fresh planner the goal, evidence, permitted scope, unit ID, and known acceptance.
Use the existing `judgment and prose` model role.
Apply [Models in poteto-mode](../../poteto-mode/SKILL.md#models), including overrides and fallback.
Give a separate planner chore its own actor. The planner does not claim or close the owner's unit.
The owner keeps its unit claim.

The planner defines scope, tasks, priorities, milestones, dependencies, and separate output scopes.
It gives the architect the current behavior, constraints, evidence, and unresolved technical questions.
The planner writes no code or tests. It selects no technical design and approves no code quality.
Return technical questions, such as database or API choices, to the architect.
Record missing product decisions and their effects. Stop dependent design and implementation until those requirements are clear.
Independent work can continue.

Select the mode with these criteria. This section is the sole mode definition.

- Use Full for new features, unclear scope, or an unresolved design decision.
- Permit Lightweight only when one sentence describes the work with no ambiguity.
  That sentence states the change and its observable result under a known contract.
- When in doubt, use Full. Diff length and file count are not criteria.
- An explicit architecture request still receives architecture.
- Lightweight permits an architect skip only for the recorded scope.
  Requirements, writer, diff review, and production-code testing remain required.
- Any agent can report a need to escalate from Lightweight to Full.
  Stop dependent implementation until the Full path supplies the required context.
- Only the requirements planner can downgrade after a new assessment.
  Record the evidence and reason before dependent work resumes.
- A changed requirement, contract, or scope returns to requirements planning.
  Stop dependent design and implementation until the new brief supplies their context.
  Reuse a brief or design approval only within its recorded scope.

Return this requirements brief:

```text
Goal
The user outcome in one sentence.

Scope and exclusions
The allowed behavior change, output paths, and excluded work.

Tasks and milestones
Each task's result, priority, and checkable acceptance.

Sequence and parallel work
Dependencies, execution order, and separate output scopes.

Architect notes
Current behavior, constraints, evidence paths, and unresolved technical questions.

Mode decision
Full or Lightweight, its reason, evidence, covered scope, and architect required or skipped.

Unresolved requirements
Missing product decisions, their effects, and independent work that can continue.
```

The owner records the complete brief in the unit description.
Keep independent done checks in the acceptance field.
Keep requirements out of the throughput design field.
Use real task dependencies, not a fixed dependency chain for independent work.

```sh
bd update <unit> --body-file <brief-file>
bd update <unit> --acceptance "<criteria>"
bd dep add <dependent> <blocker>
```

For a changed mode, record its reason and evidence in a bead comment.
Update the current mode in the unit description before dependent work resumes.
Use [Text files](../../ticket-work/references/text-files.md) for long descriptions and comments.

## Architect

Read the requirements brief and its recorded [mode decision](#requirements-planning).
This phase consumes that decision. It defines no separate skip criteria.
For a decision that requires architecture, use [Architect planning](../../poteto-mode/playbooks/architect-planning.md).
Request [architect](../../architect/SKILL.md) Phases A through C only.
Receive the sketch, rationale, artifact paths, covered implementation scope, and unresolved decisions.
The architect writes no production code. The owner commits the production sketch and rationale before sketch review.

For a recorded architect skip, close the architect step with `skip: Lightweight mode: <reason and scope>`.
Record sketch review as not applicable because no sketch exists.
Do not create and skip a required sketch gate.

## Sketch review

Review the committed sketch and rationale with the base SHA and covered scope.
Follow [Own the skeptic review](#own-the-skeptic-review).
Obtain a fresh skeptic pass before the production writer starts.
A failed review returns to the design agent with the consolidated findings.
Return unresolved product requirements to the planner and technical choices to the architect.

## Writer

Give the writer the requirements, acceptance, mode, permitted paths, and evidence.
When architecture applies, include the sketch paths, committed sketch SHA, and passed sketch gate.
Follow the task playbook within that scope through implementation and the writer's build and test checks.
Commit the implementation before the writer handoff.
Stop before the task playbook's runtime verification and PR steps.
Return the committed implementation head, complete base-to-head diff, and check evidence.
The owner resumes the remaining task-playbook steps only after the required diff review and test gates have current passes.
Those remaining steps include runtime verification and PR work.
New scope returns to [Requirements planning](#requirements-planning) before dependent work resumes.

## Diff review

Give a fresh skeptic the complete writer diff, including tests, base SHA, scope, and acceptance.
Follow [Own the skeptic review](#own-the-skeptic-review).
Obtain a current pass before the production-code tester starts.
Prose-only production work needs this review and no production-code tester.

## Tester

After the diff pass, give a dedicated tester the acceptance, suite commands, and allowed test paths.
Follow [Own the test gate](#own-the-test-gate).
Receive the verdict, test commits, final SHA, and current review coverage.
Obtain the final skeptic coverage of tester edits before runtime verification.
The owner checks all required current passes before runtime verification and handback.

## Production checks

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
Use [Shipping step 3](../../poteto-mode/playbooks/shipping.md) as the sole definition of patch equivalence.

### Own the skeptic review

1. For a sketch, commit the sketch and rationale before the review assignment.
   Before the spawn, create a gate bead under the bead that holds the work.
   Put the base SHA, scope, and done-when in its description.

   ```sh
   bd create "skeptic review: <sketch|diff> of <subject>" -t chore --parent <bead> --body-file <file> --silent
   ```

2. Spawn a fresh agent with the configured skeptic review model.
   Apply [Models in poteto-mode](../../poteto-mode/SKILL.md#models), including overrides and fallback.
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

### Own the test gate

1. After the skeptic diff pass, create a `chore` test gate under the same parent as the diff gate.
   Do not create it under the closed diff gate.
   Put the base SHA, scope, done-when, suite commands, and allowed test paths in its description.
   Name the preceding diff gate and its pass SHA.

   ```sh
   bd create "test gate: <subject>" -t chore --parent <bead> --body-file <file> --silent
   ```

2. Pause the writer while the tester runs. Give the tester exclusive write access to the allowed test paths.
   Spawn a fresh agent with the configured test model per [Models in poteto-mode](../../poteto-mode/SKILL.md#models).
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

### Return the evidence

A delegate reports both gate IDs and the final SHA. Its spawner checks valid receipts instead of repeating gates.
An agent that cannot spawn returns its head and pending gates to its spawner.
If the brief assigns diff review and testing to the spawner, the worker runs only its sketch review.
Orchestrate, Autopilot-full, Autopilot-stack, and Shipping own diff and test gates for their workers and owners.
Runtime verification follows the required current passes.
