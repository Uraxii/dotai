### Orchestrate

Resolve the driver skill through [poteto-mode's Non-negotiables](../SKILL.md#non-negotiables).

**You own the program, never the code. Author briefs, drain the queue, keep the frontier green, decide.** For a whole project handed to one standing coordinator chat: multi-day, many stacked PRs, dozens to hundreds of subagents, the human checking in twice a day instead of every five minutes. One task driven to a predicate is Autonomous run. One ambitious run needing a bespoke workflow is figure-it-out. Route here when the work outlives any single agent. Work one agent could finish inside the session's budget is not a program.

Ceremony must scale with the program. On cheap near-identical units, collapse it as each section directs.

Three rules carry the rest.

- Completions are queue events, not interrupts.
- Program state lives in beads, git, and GitHub. Read it from there at every drain, never from memory or the transcript.
- The brief is the product. A vague brief fails quietly, because a worker cannot ask you a question.

#### Roles and placement

- **Coordinator (this chat).** Frames, authors briefs, drains the queue, owns the human report, makes judgment calls. It never authors or edits code: conflicted merges, restacks, and code changes are always tasks. Mechanically landing a verified unit (fast-forward or clean cherry-pick of a worker's commit, then push) is bookkeeping the coordinator may do itself on repos where local git is cheap; queueing finished work behind an idle stacker is how a deadline harvests nothing. The loop is agentic end to end. Agents are spawned, resumed, and drained only through the `Agent` tool. State reads and writes go through `bd`, `gh`, and `git` at drain points. None of them spawns, waits, or wakes anything.
- **Sub-coordinator.** Durable, one per track, and only when the program exceeds what one coordinator's drains can manage. A track the coordinator can drain itself needs no middle layer: each nested layer re-pays a full orientation preamble, and a blocking sub-coordinator hides its children while the parent idles. Owns the units labelled with its track, authors its workers' briefs, spawns its own workers and verifiers where the runtime lets a subagent spawn one; where it does not, it owns its track's units directly with the same review separation. Rolls up aggregates at wave boundaries; never forwards raw child reports. Cap in-flight children at what one drain can process, roughly ten, as a rolling window; never as blocking batches, which cost the slowest child of every batch.
- **Worker / verifier.** Background subagents (`run_in_background: true`), each claiming one bead per [the beads work loop](../references/beads-work-loop.md). Claude Code has no remote worker environment, so isolation is a worktree or branch per writer, not a separate machine. Runtime verification goes through the driver skill; the brief names its resolved skill path or exact commands. A subagent never sees this chat, so its bead inlines what it needs or points at repo paths, PRs, and other beads. Prefer fewer, broader workers; one writer per worktree or branch (principle-separate-before-serializing-shared-state). Run a unit's verifier on a different model family from its worker.

Depth stays at coordinator, track, worker. Author the track decomposition per project. Build, landing, and verification are common cuts, not a required shape.

#### Program state

The program lives in the beads store that the session's `BEADS_DIR` names, in git, and on GitHub. All three outlive this chat, so a session restart loses only in-flight subagents.

- **Program.** One epic. Its description holds the goal and scope, and its acceptance holds the done predicate. Change them with `bd update <epic> --description "<text>"` or `--acceptance "<text>"`.

  ```sh
  bd create "<program>" -t epic --description "<goal and scope>" --acceptance "<done predicate>"
  ```

- **Tracks.** A track is a label, `track:<name>`, on each of its units. Keep every unit a direct child of the program epic, because `bd swarm status` counts only direct children. A sub-coordinator's own bead stays outside the epic: create it with `bd create "Track <name>" --label track:<name> --body-file <brief.md>`. It reads its units with `bd ready --parent <epic> --label track:<name>`.
- **Units.** One child bead per unit, with its brief in the description and its done-when in the acceptance. Order units with `bd dep add <later> <earlier>`. `bd ready` lists a dependent unit only after every unit it depends on lands.

  ```sh
  bd create "<unit>" --parent <epic> --acceptance "<done-when>" --body-file <brief.md>
  ```

  To stack a dependent unit on upstream work that has not landed, read its blockers and their stages.

  ```sh
  bd blocked --parent <epic>     # each blocked unit and the beads that block it
  bd state <blocker> stage       # built, verified, or stacked
  ```

  Spawn the dependent unit when every blocker is a unit at `built` or later. Set its base to the branch in the blocker's `ready at <SHA> on <branch>` comment, and name that branch and SHA in its brief. If the blockers sit on more than one unlanded branch, base the unit on the branch that contains the others, or wait until only one is unlanded. A gate has no stage, so a unit behind an open gate waits for the gate.

- **Unit stage.** A unit bead stays open until its PR lands. The `stage:<value>` label records where an in-progress unit is, and `bd set-state` replaces the old value and records the change.

  | Stage | Who sets it, and when |
  |---|---|
  | none, status `open` | Not started. `bd ready` lists it. |
  | none, status `in_progress` | The worker claimed it and is building. |
  | `stage=built` | The worker, after it pushes, per step 5 of [the beads work loop](../references/beads-work-loop.md). It comments `ready at <SHA> on <branch>`, clears its assignee, and leaves the bead open. |
  | `stage=verified` | Whoever records a passing verdict, per Verification. |
  | `stage=stacked` | The stacker, after the PR enters the stack. |
  | `stage=landed`, status `closed` | The coordinator, after the merge. It runs `bd set-state <id> stage=landed --reason "<merge SHA>"`, then `bd close <id> --reason "landed <merge SHA> PR <number>"`. |
  | `stage=abandoned`, status `closed` | The coordinator, per Liveness and failure. If a dead worker still holds the claim, it runs `bd unclaim <id> --if-assignee <actor>` first. The close reason says why. |

  A new head SHA sets the unit back to `stage=built`.

- **Decisions.** Each constraint the program holds (model policy, stack shape and count, verification bar, forbidden paths, escalation policy, a human ruling) is one decision bead under the epic, created with `bd create "<decision>" -t decision --parent <epic>`. For a human ruling, quote the human's words with attribution in the description, per [Claims about human decisions](../../why/references/epistemics.md#claims-about-human-decisions), and label your own interpretation. To change a decision, create the new one and run `bd supersede <old> --with <new>`. `bd list --parent <epic> -t decision --status open` lists the decisions in force. When you catch yourself restating an instruction, record it as a decision bead before you act (principle-encode-lessons-in-structure).
- **Verdicts.** A verdict is a comment on the unit bead, per Verification.
- **Gates.** A unit that waits on the human, a PR merge, or a workflow run gets a gate. The gate keeps the unit out of `bd ready` until the gate closes.

  ```sh
  bd gate create --type human --blocks <id> --reason "<question; options; default on no answer>"
  bd gate create --type gh:pr --await-id <pr number> --blocks <id>
  bd gate create --type gh:run --await-id <run id> --blocks <id>
  ```

  `bd gate list` shows the open gates. `bd gate resolve <gate> --reason "<answer>"` closes a human gate. Quote the human's answer in the reason.

  Run `bd gate check --type gh` from the repo root, because it calls `gh` against the repo in the current directory. It closes each GitHub gate whose PR merged or whose run succeeded. It exits 0 even when a check fails, so read its output, not its exit code.

  - `ESCALATE - workflow '<name>' failed`. Create a fix unit, make the gated unit depend on it with `bd dep add <gated unit> <fix unit>`, and run `bd gate resolve <gate> --reason "run <id> failed; fix in <fix unit>"`.
  - `ESCALATE - PR '<title>' was closed without merging`. Open a human gate on the gated unit that asks whether to reopen, replace, or drop the PR, then resolve the PR gate with a reason that names the human gate.
  - `error checking`. The command ran outside the repo, or `gh` failed. Fix the cause and run the check again.

  Never pass `--escalate`. It runs `gt escalate`, which is not a Graphite command.
- **PRs and stacks.** GitHub and the stacker's clone, read with `gh` and `gt` per Stack safety.
- **Messages.** A spawn prompt goes down, a final message comes up as the completion notification, and a correction to a live agent goes down with `SendMessage`.
- **The one-stacker rule.** The beads merge slot, per Stack safety.

Read the program at each drain with these commands.

```sh
bd ready --parent <epic> --exclude-type decision            # units to spawn now
bd list --parent <epic> --status in_progress --json          # assignee and stage of each unit in flight
bd swarm status <epic>                                       # completed, active, ready, and blocked counts
bd blocked --parent <epic>                                   # what blocks each unit, gates included
bd gate list                                                 # open gates
gh pr list --state open --json number,title,headRefName,baseRefName,headRefOid
```

Spawn only from `bd ready`. `bd swarm status` ignores gates, counts open decision beads as ready work, and counts abandoned units as completed, so read it for progress, not for what to spawn or for the predicate count. Count landed units with `bd list --parent <epic> --status closed --label stage:landed --json`. After you create or reorder units, run `bd swarm validate <epic>`. It rejects a dependency cycle and prints the waves of parallel work and the maximum parallelism, with decision beads in the first wave.

#### The brief

Your prompts to agents are your only product, and a sloppy brief compounds into slop across the whole tree. The brief is the unit bead's description, and the spawn prompt is the one line from [Agent runs](../SKILL.md#subagents) with `Stop at stage=built.` appended. A field you cannot fill is a unit you have not scoped yet.

```
GOAL         one sentence, the outcome, executable by a stranger with no chat access
SCOPE        paths this unit may write; paths it may not; its exclusive worktree or branch
CONTEXT      pointers to files, PRs, and upstream beads; read each upstream bead with
             bd show, because workers cannot see siblings
ACCEPTANCE   the bead's acceptance, checkable criteria, one per line
VERIFY       exact commands or the resolved driver skill path, plus known gotchas
TIMEBOX      rough cap on runtime; on expiry, return partial findings and stop rather than run on
FORBIDDEN    no gt, no rebase, no force-push, no fixes outside scope, plus unit-specific bans
REPORT       what the final message carries: status, branch, head SHA, PRs, verdict,
             what you actually ran, deviations, suggested follow-ups
DECISIONS    the ids of the decision beads that bind this unit; read each with bd show
```

Size the brief to the unit. A one-command unit gets the template collapsed to a paragraph that still names goal, scope, the verify command, and the report shape; a 4KB scaffold around a two-line edit costs more to write and obey than the edit.

A sub-coordinator's brief is the description of its track bead. It adds its track boundary, its spawn budget, the drain protocol, and the rollup format (per child: bead id, status, PR, head SHA, verdict, one line; plus track status and frontier delta).

A dependency is a context relay, not just ordering: undeclared upstream context makes the worker guess. Missing fields are a refuse-to-spawn condition. Audit one sampled worker brief per sub-coordinator per wave, concurrently with the wave it samples, never as a gate in front of it; a failing brief stops that track and fixes the sub-coordinator's instructions, not just the worker, because brief quality decays late in a run. Never resume-chain a brief. Update the bead with `bd update <id> --description "<text>"` and respawn fresh.

#### Steps

1. **Frame.** State the done predicate as something countable ("all 126 units merged, each with a `unit-test-verified` or better verdict at its merged head"). Quantify scope: units, rough effort, expected stacks, and the wall-clock budget. If one agent could finish inside that budget, stop here and run Autonomous run instead. Collapsing must not depend on another document being present: it means do the work directly in this session, plain workers where they help, verification inline, landing as you go, and none of the epic, gate, or pilot machinery below. Schedule landing against the budget: by roughly 70% of it, stop spawning and land what is verified. Name the tracks per project. A contested decomposition or one-way door goes through the arena skill before the pilot. Present the framing once; reversible prep proceeds without waiting.
2. **Create the program.** Create the epic, the decision beads, the unit beads, and their dependencies per Program state, then run `bd swarm validate <epic>`. If the program stacks PRs, create the merge slot once per store with `bd merge-slot create`. Read the open PRs the program inherits with `gh pr list`.
3. **Pilot.** Push one unit through the whole path: brief, worker, verification, stack entry, verdict comment, merge. The pilot exists to falsify the brief template, the verify recipe, and the unit size while that costs one agent instead of fifty. Fix the contract from pilot evidence before any fan-out. Scale the pilot to the unit: on programs of near-identical cheap units, the first unit is the pilot, run as a normal unit with its verify command inline, and fan-out starts the moment it lands. The dedicated pilot pipeline (separate verifier agent, audit gate) is for expensive or novel unit shapes, not for clone-units where a serialized pilot has nothing to falsify.
4. **Scale.** Spawn a rolling window of workers up to the in-flight cap, refilling as children finish; blocking batches pay the slowest child of every batch. Spawn track sub-coordinators only past the one-drain threshold in Roles. Read `bd ready --parent <epic> --exclude-type decision` after each drain; name upstream beads in downstream briefs; keep sibling communication upward only. The sampled brief audit runs alongside the wave it samples and stops the next refill on failure, not the current one.
5. **Drain.** Run the queue discipline below at every drain point.
6. **Land.** Landing is continuous, never a terminal phase: integration starts with the first verified unit and runs alongside the remaining waves. On heavy repos the stacker is a standing role from wave one, integrating as units verify; on repos where local git is cheap, the coordinator lands verified units itself per Roles. Keep the frontier green before upper-stack work; Stack safety governs. Recompute the frontier after each merge or reported new head SHA.
7. **Close.** Drain the final completions. Reconcile every unit bead to `stage=landed` or `stage=abandoned` and close it, with a reason that says landed, abandoned, or zombie-reconciled. Confirm the predicate on the real artifact, and confirm every landed PR has a verdict for its current head SHA. Record recurring corrections as decision beads or fold them into the brief template. Close the decision beads and the track beads, then close the epic with `bd close <epic> --reason "<the predicate count and the PR links>"`. The closed epic and its children are the postmortem.

#### Queue and drain

- On a completion notification, note the bead id and return to what you were doing. Never deep-review inline; a completion that needs review becomes a verifier unit. Never review a diff inside a drain.
- Drain in batches at four points: the end of a critical section, a track rollup, a frontier watcher wake (arm it via the loop skill, with a long heartbeat fallback), and before a human report. Begin each batch with `bd show <id>` for every bead whose completion arrived since the last drain. Arrivals during a drain wait for the next one.
- Critical sections you finish first: authoring a brief, a stack operation, a conflict decision, opening a gate, recording a verdict.
- Each drain classifies every completion (landed, needs-verify, failed, zombie, noise) and records the result on its bead per the stage table in Program state, with `bd comment`, `bd set-state`, or `bd close`. Then it runs `bd gate check --type gh`, reads the program per Program state, and spawns the next wave in one message.
- Account for every spawned child at its track's rollup: arrived, respawned, or its scope explicitly absorbed. Silently redoing a missing child's work hides both the wasted spend and the coverage gap its result existed to close.
- A drain turn ends with three lines: the counts from `bd swarm status <epic>`, what changed, and the open gates from `bd gate list`. The full reply contract applies at checkpoints and close.

#### Stack safety

- The frontier is a computed object, never narrative: the ordered PR list with branch names and head SHAs, and the lowest unmerged PR. Recompute it after every merge and stack mutation. Resolve it in the stacker's clone, because GitHub base refs drift mid-restack while gt tracking is authoritative.

  ```sh
  gt log short --stack --reverse                          # stack branches, trunk first
  gh pr view <branch> --json number,state,headRefOid      # once per branch, bottom up
  ```

  The lowest unmerged PR is the first `OPEN` one. If `gh pr view` finds no PR for a branch, that branch has no PR on GitHub. Ask the stacker to submit it, and never guess a PR number. For a stack that gt does not track, follow `baseRefName` up from trunk in `gh pr list --state open --json number,headRefName,baseRefName,headRefOid`.
- Exactly one stacker at a time may run `gt` or rewrite a stack, and the beads merge slot enforces it. The slot covers the whole beads store, not one program, so it serializes every stack of every program that shares the store. A restack at this scale is slow and blocks whoever runs it, so give it its own unit and keep the coordinator out of it.
  - The stacker runs `bd merge-slot acquire` before its first stack command. If another actor holds the slot, the command exits 1. Stop and report the holder. Run `acquire` again after the holder releases. Nothing wakes a waiting stacker.
  - After each PR enters the stack, the stacker runs `bd set-state <id> stage=stacked --reason "PR <number> at <SHA>"` on its unit.
  - The stacker that acquired the slot releases it with `bd merge-slot release --holder <actor>` after its last push and before it reports, inside the same unit. Always pass `--holder`. A release without it frees the slot whoever holds it.
  - The slot has no lease. If its holder dies, the coordinator confirms the holder has no live agent, then runs `bd merge-slot release --holder <dead actor>`. `bd merge-slot check` names the holder.
- Workers never rebase and never run `gt`. Babysitters follow `playbooks/babysit.md`, one per stack, scoped to the PR numbers and head SHAs in their brief; a new head SHA ends that scope. They report conflicts to the stacker rather than restacking.
- PR closes and retargets go through the stacker only; closing a base PR orphans every chain above it. Merges and stack surgery are units with briefs like any other.
- One retro watcher follows merged PRs for reverts, post-merge CI breaks, and orphaned follow-ups.

#### Verification

Scale verification to the unit. When VERIFY is a single cheap command, the worker runs it and reports the output, and the coordinator spot-checks receipts; a dedicated verifier agent (on a different model family than the worker) is for units whose verification is expensive, judgment-laden, or high-blast-radius. A verifier agent whose entire product would be rerunning one command is ceremony, not verification.

Record each verdict on the unit bead, keyed by PR number and head SHA.

```sh
bd comment <id> "verdict <verdict> at <SHA> on PR <number>"
bd set-state <id> stage=verified --reason "<verdict> at <SHA>"   # passing verdicts only
```

The verdict is one of `live-ui-verified`, `unit-test-verified`, `type-check-only`, `verifier-blocked`, or `verifier-failed`. To check that a verdict is current, compare its SHA with `gh pr view <number> --json headRefOid`. CI green is an input to a verdict, not a verdict. Behavioral work needs better than `type-check-only`. `verifier-blocked` is not a pass; respawn when the environment heals. `verifier-failed` gets a fix unit, not a re-verify. A worker may self-report; a verifier's later comment on the same PR and SHA overrides it. A new head SHA voids the verdict. Set the unit back to `stage=built` and re-verify after restack. The bead's comments answer "was this verified", not memory and not the transcript.

A unit is not done until its output is externalized the moment it lands, never batched to the end of the run: a worker pushes its branch and comments its ready SHA, a verifier comments its verdict, receipts land on the bead. Work that exists only on one VM when that VM dies was never done.

#### Liveness and failure

- Never resume an agent to check on it; a resume restarts an idle agent. Probe read-only: `bd show <id>` and its lease, `gh`, pushed branches, and the background task list. Transcript mtime is not liveness.
- Record a silent death on its bead with `bd comment <id> "died: <failure mode>; last evidence <what>; options <what>"`, then recover the bead per [the beads work loop](../references/beads-work-loop.md). Replan on evidence as it arrives; never wait for full quiescence.
- Retry by mode: cap-hit or oom, respawn with smaller scope; network-drop, retry as-is; tool-error, retry on a different model; unknown, retry once. Two retries, then abandon the unit per the stage table and replan around it.
- A zombie that returns hours late reconciles against the current frontier and the bead's verdicts before anything is accepted. Salvage unique findings through a fresh unit, never a blind merge.
- When continued spawning would produce garbage tree-wide (bad upstream output, broken acceptance, dead infra), create a decision bead `Hold: no spawns until <cause> is fixed` and send it to every sub-coordinator with `SendMessage`. Let in-flight work finish, fix the cause, then close the hold bead with the fix as its reason.
- Bound your own infra retries the same way you bound a child's. After a few consecutive tool aborts, stop retrying: comment a terminal handoff on the epic (what is done, where it lives, the exact command to resume) and end the run.
- After a session restart, in-flight subagents are dead. Pushed branches, open PRs, and the beads store are not. Read the epic and its open decisions. Run `bd list --parent <epic> --status in_progress --json` and read each unit's stage label and assignee. A unit with no stage label was mid-build, so respawn its worker under the same actor. A unit at `stage=built` needs a verdict, `stage=verified` needs a stack entry, and `stage=stacked` needs a land. Run `bd merge-slot check` and recompute the frontier. Reattach in-flight work by PR and branch rather than agent id. List the track beads with `bd list --label-pattern 'track:*' --no-parent --status open` and each track's open units with `bd list --parent <epic> --label track:<name> --json`. Respawn one sub-coordinator per track from its track bead, drain, and resume. A merge slot held by a dead agent stays held until you release it per Stack safety.

#### Escalation

Reaches the human, batched into the next human report rather than per item: irreversible actions (force-push to shared branches, deploys, deletions, closing someone else's PR), genuine product or preference calls no experiment settles, a decision bead that contradicts observed reality, a program-level dead end that survived a replan. Before asking, park each as a human gate on the bead it blocks, and route work around it. When the human answers, resolve the gate with the answer quoted. A ruling that binds later units also becomes a decision bead.

Never reaches the human: frontier nudges, restack mechanics, retries, CI flake triage, review-thread triage, format fixes, scope the brief already forbids (refuse and continue), and "should I keep going". When in doubt, act and log.

Mid-run discoveries fix only what blocks the frontier. Everything else parks in follow-up beads; at this fan-out a small scope leak multiplies into PRs nobody asked for.

**Reply:** at checkpoints and close: the predicate and the count of `stage:landed` units against it, tracks and what each landed, the frontier (PR list plus SHAs), verdicts summary from the bead comments, what was abandoned and why, open gates from `bd gate list` (the only asks), and the epic id. Numbers from `bd` and `gh`, not narrative. Include PR links.
