# Run records

Each playbook run or phased skill records its steps as beads in the database at `BEADS_DIR`.
This reference matches bd 1.3.1. Use `bd help <command>` for the exact flags.
Use the beads access that your harness supplies. The `bd` form defines the exact behavior.

## The run bead

The run bead holds one run. Its child beads hold the steps.

1. Find or create the run bead.
   An assignment to review, verify, or test a named bead does not claim that bead. The writer holds that claim.
   The reviewer, tester, or Orchestrate verifier creates its own run bead.

   - If you hold a run bead for this task, keep it across playbook and phased-skill calls.
   - If your prompt tells you to claim a bead, use that bead as the run bead.
   - An Orchestrate worker uses its unit bead. The coordinator claimed it under the worker's actor name.
   - Otherwise, create a run bead with no parent. A subagent that runs a playbook creates its own run bead.
   - An Orchestrate coordinator also creates its own run bead. The program epic is a different bead.

   ```sh
   bd create "<playbook>: <task>" --silent
   ```

   The `--silent` flag prints only the new ID.
   If creation exits 1 with `no beads database found`, initialize a database. Then repeat creation.
   If `BEADS_DIR` is set, first create its parent directory. The init command exits 1 when that directory is absent.
   Run initialization at the repository root.

   ```sh
   mkdir -p "$(dirname "$BEADS_DIR")"
   bd init --non-interactive --skip-agents --skip-hooks
   ```

   The `--skip-agents` and `--skip-hooks` flags prevent writes to agent instruction files and git hooks.

2. If your prompt gives an actor name, set `BEADS_ACTOR=<actor>` on each `bd` call.
   Each shell call starts fresh. bd records claims and history under this actor name.
3. Claim the run with `bd update <run> --claim`.
   If another actor holds it, the command exits 1 and changes nothing. Stop and report the holder.
4. At the end, close the run with `bd close <run> --reason-file <file>`.
   State what changed, the proof, and the SHA in the reason.
   If your prompt specifies a different end state, use that state.
   For example, `Stop at stage=built.` leaves the run open with `bd set-state <run> stage=built`.
5. Name the run bead ID in your final message. The reader can then list its step beads.

## Step beads

1. Before other work, create one child bead for each playbook step in playbook order.
   Use the step number and its first sentence as the title.
   Copy the step text verbatim into the description file, per [Text files](text-files.md).

   ```sh
   bd create "<n>. <first sentence of the step>" -t chore --parent <run> --body-file <file> --silent
   ```

2. Then create a step bead for each task-specific item with the same command.
3. At the start of a step, claim it with `bd update <step> --claim`.
4. At completion, close it with the result and evidence pointer.
   Use `bd close <step> --reason "<result>, <evidence>"`.

Use type `chore` for step beads.
The command `bd ready --parent <epic> -t task` lists every task descendant of an epic.
Task-type steps would appear as units ready for an Orchestrate worker.

## Skip a step

To omit a step, close it with a one-line reason that starts with `skip:`.

```sh
bd close <step> --reason "skip: <reason>"
```

The closed bead stays in the database as evidence of the skip.
A step that forbids a skip cannot close this way.

## Switch playbooks

1. Close each open step with `skip: switched to <playbook>`.
2. Create the new playbook's step beads under the same run, per Step beads.
3. Keep the run bead. Do not create another run.
4. Change its title with `bd update <run> --title "<playbook>: <task>"`.

For example, an Orchestrate Frame step can select Autonomous run.
The coordinator closes the open Orchestrate steps and adds the Autonomous run steps to the same run.

## Phases of a skill

Before the first phase, create one `chore` child bead for each phase.
The architect, arena, swarm, and run-workflow skills are phased.
Use the step that runs the skill as the parent. If no step runs it, use the run bead.
If no run exists, first create one per The run bead.

## The throughput checkpoint

Write one line for each dimension into the run's design field.
For a dimension that does not apply, keep its line as `n/a: <reason>`.

```sh
bd update <run> --design-file <file>
```

To replace the checkpoint, repeat the command. Use `bd show <run>` to read it.

## Read the run

- Use `bd list --parent <run> --all` to list step beads and their status. Without `--all`, bd hides closed beads.
- Use `bd show <step>` to read one step's close reason.
- Use `bd list --parent <run> --all --json` to read every step's `close_reason`.

## End the run

The command `bd close` exits 1 if a bead has an open child.
Close all steps before you close the run, set its stage, or end your turn with a report.

## Agents that cannot reach the database

A cloud agent cannot reach the beads database. It keeps no step beads.
Its final message lists each step with its result or `skip: <reason>`.
The spawner writes that list to a file and records it with `bd comment <id> --file <file>`.
Use the bead assigned to the cloud agent.

## Proof that claims and closes survive concurrency

The loop depends on two bd behaviors.
If several actors claim one bead at once, exactly one wins.
If several processes close different beads at once, every close lands.

The [concurrency script](../../poteto-mode/scripts/check_bd_concurrency.py) races both operations on a temporary store, ten rounds each.
It exits 1 on the first failure. It needs bd on PATH and does not run automatically.
Run it after a bd upgrade.

```sh
python3 ../../poteto-mode/scripts/check_bd_concurrency.py
```

Run this command from the reference directory. Ten rounds take about 2.5 minutes.
