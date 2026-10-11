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
