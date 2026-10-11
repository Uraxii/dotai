# Beads work loop

Each run of a playbook or of a phased skill keeps its steps as beads in the beads database at `BEADS_DIR`. This reference matches bd 1.3.1. `bd help <command>` gives the exact flags. Run each operation with the beads access that your harness gives you. The `bd` form defines the exact behavior.

## The run bead

The run bead holds one run, and its child beads hold the steps.

1. Find or create the run bead.

   An agent whose prompt names a bead to review, verify, or test does not claim that bead, because the writer holds the claim. An Orchestrate verifier, a reviewer, and a tester are examples. Such an agent creates its own run bead.

   - If you already hold a run bead for this task, keep it. This holds when a playbook sends you to another playbook or a phased skill.
   - If your prompt tells you to claim a bead, that bead is the run bead.
   - An Orchestrate worker's run bead is its unit bead. The coordinator claimed the unit under the worker's actor name.
   - Otherwise, create the run bead with no parent. A subagent that runs a playbook creates its own run bead. An Orchestrate coordinator also creates its own run bead. The program epic is a different bead.

   ```sh
   bd create "<playbook>: <task>" --silent
   ```

   `--silent` prints only the new ID. If `bd create` exits 1 with `no beads database found`, initialize a database and run `bd create` again. If `BEADS_DIR` is set, first create its parent directory, because `bd init` exits 1 when that directory does not exist. Run `bd init` at the repository root.

   ```sh
   mkdir -p "$(dirname "$BEADS_DIR")"
   bd init --non-interactive --skip-agents --skip-hooks
   ```

   `--skip-agents` and `--skip-hooks` stop bd from writing agent instruction files and git hooks into the repository.

2. When your prompt gives an actor name, set `BEADS_ACTOR=<actor>` on each `bd` call. Each shell call starts fresh, so set it on every call. bd records claims and history under this name.
3. Claim the run bead (`bd update <run> --claim`). If another actor holds it, the claim exits 1 and changes nothing. Stop and report the holder.
4. At the end, close the run bead with a reason that says what changed, the proof, and the SHA (`bd close <run> --reason-file <file>`). If your prompt tells you to end it another way, do that instead. For example, `Stop at stage=built.` leaves the bead open with `bd set-state <run> stage=built`.
5. Name the run bead ID in your final message, so the reader can list its step beads.

## Step beads

1. Before any other work, create one child bead for each step of the playbook, in the order of the playbook. The title is the step number and the first sentence of the step. The description is the step text, copied verbatim from a file, per Text with quotes or several lines.

   ```sh
   bd create "<n>. <first sentence of the step>" -t chore --parent <run> --body-file <file> --silent
   ```

2. Then create one step bead for each task-specific item, with the same command.
3. When you start a step, claim its step bead (`bd update <step> --claim`).
4. When you finish a step, close its step bead with the result and a pointer to the evidence (`bd close <step> --reason "<result>, <evidence>"`).

Step beads have the type `chore`, because `bd ready --parent <epic> -t task` lists every `task` descendant of an epic, and Orchestrate would show a `task` step bead as a unit that is ready to spawn.

## Skip a step

To not do a step, close its step bead with a one-line reason that starts with `skip:`.

```sh
bd close <step> --reason "skip: <reason>"
```

The closed bead stays in the database, so the skip stays visible. A step that says it has no skip cannot close this way.

## Switch playbooks

When a run changes to a different playbook, close each open step bead with `skip: switched to <playbook>`. Then create the step beads of the new playbook under the same run bead, per Step beads. Do not create a second run bead. Change the run bead's title to name the new playbook (`bd update <run> --title "<playbook>: <task>"`). For example, when the Orchestrate Frame step collapses the program to Autonomous run, the coordinator closes the open Orchestrate step beads and adds the Autonomous run steps.

## Phases of a skill

Before a phased skill starts its first phase, create one `chore` child bead for each phase. The **architect**, **arena**, **swarm**, and **figure-it-out** skills are phased. The parent is the step bead that runs the skill. When no step runs the skill, the parent is the run bead. If you have no run bead, create one first, per The run bead.

## The throughput checkpoint

Write the throughput checkpoint into the design field of the run bead, one line for each dimension. A dimension that does not apply keeps its line as `n/a: <reason>`.

```sh
bd update <run> --design-file <file>
```

To rewrite the checkpoint, run the same command again. It replaces the field. `bd show <run>` prints the checkpoint.

## Read the run

- `bd list --parent <run> --all` lists the step beads with their status. Without `--all`, bd hides the closed beads.
- `bd show <step>` prints the close reason of one step bead. `bd list --parent <run> --all --json` gives the `close_reason` of each step bead.

## End the run

`bd close` exits 1 on a bead that has an open child. Close every step bead before you close the run bead, set its stage, or end your turn with a report.

## Agents that cannot reach the database

A cloud agent cannot reach the beads database, so it keeps no step beads. Its final message lists each step with its result or `skip: <reason>`. The spawner writes that list to a file and adds it as a comment on the bead that it gave the agent (`bd comment <id> --file <file>`).

## Architect planning

Before each code change, obtain an architect plan. The owner may skip planning for a very small change.

1. Use the step bead that runs planning. If the code-writing step has no planning bead, create a `chore` child under that step.
2. For a very small change, the owner records the scope and reason before implementation. Close the planning bead with `skip: very small change: <reason>`. This skip applies only to architect planning. Implementation delegation, tests, the diff review, and the tester gate still apply.
3. Otherwise, claim the planning bead under the planner's actor before the spawn. Spawn a fresh `poteto-agent` using your configured architect planning model. Follow the override and fallback rules in [Models](../SKILL.md#models).
4. Give the planner a brief with the worktree, scope, constraints, done-when, output paths, and grounding evidence. Request [architect](../../architect/SKILL.md) Phases A through C only. The plan names the caller's usage, types, signatures, modules, and implementation step.
5. For production work, the planner commits the synthesized sketch and rationale. Run the existing sketch review before the handoff. The planner implements no production logic.
6. The planner returns the artifact paths, sketch SHA, gate bead, implementation scope, and unresolved decisions. Close its Phase D bead with `skip: implementation belongs to the writer`. Close unused Phase E with `skip: no architecture scrap needed`. If the sketch needs a scrap, use the existing redesign loop.
7. The owner checks the passed sketch gate per Gates below. After three sketch failures, follow that procedure's stop and escalation. Close the planning step only after the handoff and gate checks pass. The planner does not close an Orchestrate unit.
8. Give the writer the plan, sketch SHA, passed gate, and implementation scope. A plan can cover a defined batch of related edits. Do not run architect again for work that the plan already covers.
9. A change outside the plan's scope needs a new plan or the owner's very-small-change skip. A new requirement, changed contract, or failed shape returns to architect planning.

An agent that cannot reach beads follows Agents that cannot reach the database above. An agent that cannot spawn returns the planning need to its spawner before implementation. The spawner obtains the plan or records the owner skip. A writer's private task list does not replace the architect design package.

## Gates

A gate is a production check by an independent agent. A skeptic reviews the work. A dedicated tester checks production code after the skeptic diff pass. Work for production passes its gates before it ships. Work is for production when a PR will carry its commits. A Prototype, an Investigation, and an Eval run have no gate, and neither does a plan. An `interrogate` panel is not a gate. A gated step has no `skip:` when the work is for production.

| Gate | Reviews | Runs | Fixer |
| --- | --- | --- | --- |
| Sketch review | The committed `architect` sketch and its rationale | After the synthesis, before implementation | The agent that ran `architect` |
| Diff review | The writer's commits from the base to the head, including tests | After the writer reports its head SHA | The writer, or a fresh writer with consolidated scope when the writer has ended |
| Test gate | Available test quality, missing coverage, and all applicable tests | After the skeptic diff pass for production code | Tester for test defects, writer for production defects |

Sketches and prose-only changes need no test gate. Writers choose whether to add tests. Production-code changes need both a current skeptic pass and a current tester pass before runtime verification and shipping. `tdd` is the bug-test workflow. It does not replace the dedicated tester.

The following steps apply to skeptic review gates.

1. Before the spawn, create the gate bead as a child of the bead that holds the work. Its description names the base SHA, the scope, and the done-when.

   ```sh
   bd create "skeptic review: <sketch|diff> of <subject>" -t chore --parent <bead> --body-file <file> --silent
   ```

2. Spawn a fresh `poteto-agent` subagent using your configured skeptic review model (see Models in `poteto-mode`). Its prompt is exactly `Review bead <gate> at <SHA> in <worktree>.` Its actor name is `skeptic-<gate>`.
3. On `verdict fail`, send the fixer its brief plus `Fix bead <gate> at <SHA> in <worktree>.` After the fixer reports a new head, spawn a fresh reviewer at that head with the same prompt form.
4. A gate bead takes at most three `verdict fail` comments. After the third, leave the gate bead open, stop the gated work, and report the open must-fix items to the user. Work that does not depend on it goes on.
5. After `verdict pass at <SHA>`, do not review the diff again. `bd comments <gate> --json` gives the author and the text of each verdict. Check these facts:
   - The pass is the last verdict on the gate bead.
   - Its author wrote none of the work.
   - Each item of the last failed round and any linked test failure is marked `fixed` or `answered` by the reviewer.
   - For a diff review, the patch is still the one reviewed, per the patch-id rule in `playbooks/shipping.md` step 3.

   Then close the gate bead (`bd close <gate> --reason "pass at <SHA>"`). Read the diff only when a check fails.

### Own the test gate

After the skeptic diff pass, create a `test gate: <subject>` bead of type `chore`. Use the same parent as the diff gate, not the closed diff gate. Before the spawn, put the base SHA, scope, done-when, suite commands, and allowed test paths in its description. Name the preceding diff gate and its pass SHA.

```sh
bd create "test gate: <subject>" -t chore --parent <bead> --body-file <file> --silent
```

Pause the writer while the tester runs. Give the tester exclusive write access to the allowed test paths. Spawn a fresh `poteto-agent` using your configured test model. Apply the override and fallback rules in Models in `poteto-mode`. Its prompt is exactly `Test bead <gate> at <SHA> in <worktree>.` Its actor is `tester-<gate>`. The tester must have written none of the production code.

On `tests fail`, give the writer its full brief, the test findings, and `Fix bead <gate> at <SHA> in <worktree>.` Keep the same unit and test gate for retries. After the writer reports its new head, obtain a fresh skeptic diff pass, then spawn a fresh tester. A test gate takes at most three `tests fail` comments. After the third, leave it open, stop dependent work, and report the remaining failures and blockers. Independent work can continue.

Before the fresh skeptic spawn, name the test gate in the diff gate's description. Include the latest test failure and the writer's answers, especially disputed test contracts. Require the reviewer to assess each item and the preserved tester assertions. An unresolved contract dispute blocks the skeptic pass. If the reviewer confirms a wrong test contract, give that finding to the next tester to correct the test.

Before closure, check the last test verdict, its author, and its final committed SHA with `bd comments <gate> --json`. The last verdict must pass. Its author must have written no production code. Each prior failed item must be fixed or answered. The pass must cover the final patch. Also check a current skeptic pass that includes every tester edit. Then close the test gate with `bd close <gate> --reason "pass at <SHA>"`.

Test-only commits change the reviewed diff. Obtain a fresh skeptic pass on that final patch before accepting the tester pass. If that review changes nothing, retain the tester's suite results. If the review requests a change, repeat the applicable gates at the new head. A production fix invalidates both passes. Pure restacks retain evidence only under the stable patch-id rule in `playbooks/shipping.md` step 3. A changed assertion requires fresh review and test evidence. Build equivalence cannot prove assertion quality.

A delegate reports both gate IDs and the final SHA. Its spawner checks those passes instead of repeating valid gates. An agent that cannot spawn returns its head and pending gates to its spawner. When the brief assigns diff review and testing to the spawner, the worker runs only its sketch review. Orchestrate, Autopilot-full, Autopilot-stack, and Shipping own the diff and test gates for their workers and owners.

## Run a skeptic review

This section is for the agent whose prompt is `Review bead <gate> at <SHA> in <worktree>.`

1. Set `BEADS_ACTOR=skeptic-<gate>` on each `bd` call. Create your own run bead, per The run bead item 1. Edit no file in the worktree and commit nothing.
2. Read the base, the scope, and the done-when (`bd show <gate>`), and the earlier rounds (`bd comments <gate>`). The last failed round is the most recent `verdict fail at <SHA>` comment. For a linked test gate, read its description and comments too. Read the latest `tests fail at <SHA>` findings and the writer's answers.
3. Review `git diff <base>..<SHA>` in the worktree. For a sketch, also read the rationale it names. Judge the work by the **principle-skeptical-review** skill. If there is a last failed round at `<old SHA>`, read `git diff <old SHA>..<SHA>` first, because those commits are the fixes.
4. Assess each linked test finding and answer against the done-when and the preserved tester assertions. Resolve each disputed contract before passing. Edit no tests. Write the verdict to a file outside the worktree. The first line is `verdict pass at <SHA>` or `verdict fail at <SHA>`. Then list the findings under the three tiers. Mark each item of the last failed review round and linked test failure `fixed`, `answered: <reason>`, or `still open`. Add the file as a comment (`bd comment <gate> --file <file>`).

## Run a tester gate

This section is for the agent whose prompt is `Test bead <gate> at <SHA> in <worktree>.`

1. Set `BEADS_ACTOR=tester-<gate>` on each `bd` call. Create and claim your own run bead, per The run bead. Do not claim the writer's bead or the gate. Read the named gate, prior rounds, and passing skeptic gate. Confirm the input head and exclusive test-write scope before edits.
2. Read the full base-to-head diff, done-when, and all available tests. Identify absent coverage when the writer supplies no tests. Read the **principle-test-behavior-not-implementation** skill. Check meaningful assertions and real subject execution. Check errors, empty inputs, boundaries, and regressions relevant to the change. Derive incidental structure from actual state instead of assuming order or counts.
3. Design the missing cases. Choose unit, integration, or browser tests that fit the contract. Load required real fixtures. A missing fixture or test prerequisite is a blocker. Do not fabricate success.
4. Add or correct tests in the existing harness within the allowed paths. Edit no production code. Do not change a frozen parity or measurement baseline. Correct a proven stale writer test only with contract evidence and equivalent behavior coverage. Never remove a valid requirement to obtain green output. Commit test changes with a Conventional Commit subject and a body that states the reason.
5. Run all applicable tests, including new cases and adjacent regressions. Record each command, exit code, result, coverage gap, and environment blocker. A known failure still fails the all-tests-pass condition.
6. For a production defect, report the reproduction and failing assertion to the owner. Keep the failing test committed for the writer. Do not fix production code.
7. Write the verdict to a temporary file. Add it with `bd comment <gate> --file <file>`. The first line is `tests pass at <final SHA>` or `tests fail at <final SHA>`. Use the actual committed head after tester edits. Name unresolved quality findings, missed coverage, and suite failures. Mark prior failed items fixed, answered, or still open.
8. Report the final head and test commits. If tests changed the patch, request the final skeptic review. Close your own step and run beads before return. The owner closes the gate.

A pass requires complete quality checks, required coverage, and successful suite execution. A green count alone is insufficient. An unavailable environment yields `tests fail` with a blocker description. It cannot count as a pass.

## Fix a failed round

This section is for the agent whose prompt has `Fix bead <gate> at <SHA> in <worktree>.`

1. Read the review and test comments that apply to the current head (`bd comments <gate>`). Read the gate description for related gate IDs.
2. Fix each must-fix item and each failing test in the responsible code. Preserve tester-committed tests. If a tester test has a wrong contract, explain why in a comment and leave the test for the fresh reviewer.
3. Fix each should-fix-or-explain item, or answer it with a comment on the gate bead (`bd comment <gate> --file <file>`) that holds the line `answered: <item>: <reason>`.
4. Commit, and report the new head SHA. The owner obtains a fresh skeptic diff review before the next tester round.

## Text with quotes or several lines

The shell runs backticks and `$(...)` inside double quotes, and a quote in the text ends the string early. Put multi-line text, or text that holds a quote, a backtick, or `$(...)`, in a file and pass the file. Write the file with a quoted heredoc (`<<'EOF'`) or your harness's file tool.

| Text | Command |
| --- | --- |
| Close reason | `bd close <id> --reason-file <file>` |
| Comment | `bd comment <id> --file <file>` |
| Description | `bd update <id> --body-file <file>` |

Use `-` in place of `<file>` to read the text from stdin. `bd comment` takes `--stdin` for the same purpose. Short text with no quote, backtick, or `$` can stay inline.

## Proof that claims and closes survive concurrency

The loop depends on two bd behaviors. When several actors claim one bead at once, exactly one wins. When several processes close different beads at once, every close lands.

[`scripts/check_bd_concurrency.py`](../scripts/check_bd_concurrency.py) races both on a throwaway store in a temp dir, 10 rounds each, and exits 1 on the first failure. It needs bd on PATH, so nothing runs it automatically. Rerun it after a bd upgrade.

```sh
python3 scripts/check_bd_concurrency.py
```

Run the command from this skill's directory. Ten rounds take about 2.5 minutes.
