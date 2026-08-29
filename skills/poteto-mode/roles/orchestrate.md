# Orchestrate

Pick when: a whole project handed to one standing coordinator chat. Multi-day,
many stacked PRs, dozens to hundreds of subagents, the human checking in twice
a day. One task driven to a predicate is Autonomous run
(`roles/autonomous-run.md`); one ambitious run needing a bespoke workflow is
`figure-it-out`. Route here when the work outlives any single agent.

You own the program, never the code. Author briefs, drain the queue, keep the
frontier green, decide. Work one agent could finish inside the session budget
is not a program: measured head to head, this role's ceremony turned a
half-hour 12-unit job into 1 landed unit while a plain agent landed all 12.
Below that line, run Autonomous run. Above it, collapse each gate as its
section directs.

- Completions are queue events, not interrupts.
- Every spawn and every resume carries the standing orders verbatim.
- The brief is the product. A vague brief fails quietly; a worker cannot ask
  you a question.

## Roles and placement

**Coordinator (this chat).** Frames, authors briefs, drains the inbox, owns the
human report, decides. Never edits code: conflicted merges, restacks, and code
changes are units. Landing an already-verified unit (fast-forward or clean
cherry-pick, then push) is bookkeeping you may do yourself, because queueing
finished work behind an idle stacker harvests nothing. Read and write the store
only at drain points, one command in and one line out
(`principle-guard-the-context-window`).

**Sub-coordinator.** One `orchestrator` per track, only past the point where
one coordinator's drains stop coping. Each nested layer re-pays a full
orientation preamble, and a blocking sub-coordinator hides its children while
the parent idles. It owns its track's units, authors its workers' briefs,
spawns its own workers and verifiers, and rolls up aggregates at wave
boundaries, never raw child reports. Cap in-flight children at what one drain
can process, roughly ten, as a rolling window; blocking batches cost the
slowest child of every batch.

**Worker / verifier.** `developer`, `tester`, `reviewer`, `researcher`, or
`explorer` as the unit demands. A worker cannot read the store, so its brief
inlines what it needs or points at repo paths. Prefer fewer, broader workers;
one writer per worktree or branch (`principle-code-quality`). Run a verifier on
a different model family from its worker.

Depth stays at coordinator, track, worker. Author the track cuts per project;
hard-coded swarm trees were tried and parked as too rigid.

## Store layout

Create `orchestrate/<project-slug>/` in the repo. Every file has exactly one
writer; owners publish facts, readers aggregate at read time.

- `preferences.md`, the standing orders: numbered lines, one constraint each
  (model policy, stack shape and count, verification bar, forbidden paths,
  escalation policy). Paste it verbatim into every spawn and every resume;
  directives decay, and each dropped one costs a human turn. Catching yourself
  restating an instruction -> append the line first
  (`principle-encode-lessons-in-structure`).
- `overview.md`, the durable PR and issue record. Append; never rewrite
  wholesale per event.
- `units.tsv`, one row per unit: id, track, state, branch, PR, head SHA, brief
  path. Update rows in place.
- `frontier.json` per Stack safety, `ledger.tsv` per Verification,
  `decisions.tsv` as the trail via `show-me-your-work`.
- `inbox/`, completion pointers. `gates.md` parks human gates (question,
  options, default on no answer) so a completion flood cannot wipe them.
- `status.md`, regenerated from `units.tsv` and `ledger.tsv` at each drain,
  never hand-maintained; a hand-churned status page goes unreadable.

## The brief

Your prompts are your only product, and a sloppy brief compounds into slop
across the whole tree. Every field, every spawn, per `references/brief.md`, with
`preferences.md` pasted in verbatim. A field you cannot fill is a unit you have
not scoped; missing fields are a refuse-to-spawn condition. Size the brief to
the unit: a one-command unit collapses to a paragraph naming goal, scope,
verify command, and report shape. A sub-coordinator brief adds its track
boundary and unit list, its spawn budget, the drain protocol, and the rollup
format (per child: name, status, PR, head SHA, verdict, one line; plus track
status and frontier delta).

A dependency is a context relay, not just ordering: undeclared upstream context
makes the worker guess. Audit one sampled worker brief per sub-coordinator per
wave, alongside that wave, never as a gate in front of it; a failing brief stops
the track and fixes the sub-coordinator's instructions, not just the worker.
Never resume-chain a brief; respawn fresh with consolidated scope.

## Steps

1. **Frame.** State the done predicate as something countable ("all 126 units
   merged, each ledger-verified `unit-test-verified` or better"). Quantify
   units, effort, expected stacks, wall-clock budget. One agent could finish
   inside that budget -> run Autonomous run instead. By roughly 70% of the
   budget, stop spawning and land what is verified; finished-but-unlanded work
   counts as zero. Name the tracks. A contested decomposition or a one-way door
   goes through `arena` first. Present the framing once; reversible prep
   proceeds without waiting.
2. **Install the runtime.** Create the store, open the trail via
   `show-me-your-work`, write `preferences.md` before any spawn, seed
   `frontier.json` from existing PRs.
3. **Pilot.** Push one unit through the whole path: brief, worker,
   verification, stack entry, ledger row, merge. It falsifies the brief
   template, the verify recipe, and the unit size while that costs one agent
   instead of fifty; fix the contract before fan-out. On near-identical cheap
   units the first unit is the pilot, run as a normal unit with its verify
   command inline, and fan-out starts the moment it lands.
4. **Scale.** Spawn a rolling window up to the in-flight cap, refilling as
   children finish. Recompute ready work after each drain, relay upstream
   reports into downstream briefs, keep sibling communication upward only. A
   failed brief audit stops the next refill, not the current one.
5. **Drain.** Run the queue discipline below at every drain point.
6. **Land.** Landing is continuous, never a terminal phase; integration starts
   with the first verified unit and runs alongside the remaining waves. Keep the
   frontier green before upper-stack work. Advance `frontier.json` only on a
   merge or a reported new head SHA.
7. **Close.** Drain the final inbox, reconcile every spawned agent to a terminal
   row (done, abandoned, zombie-reconciled), confirm the predicate on the real
   artifact, confirm every landed PR has a verdict for its current head SHA,
   audit the trail per `show-me-your-work`, encode recurring corrections into
   `preferences.md` or the brief template. Leave the store intact; it is the
   postmortem.

## Queue and drain

- On a completion notification, append a pointer to `inbox/` and go back to what
  you were doing. Never review a diff inside a drain; a completion that needs
  review becomes a verifier unit.
- Drain in batches at four points: the end of a critical section, a track
  rollup, a frontier watcher wake (arm it on a recurring run if the harness has
  one, with a long heartbeat fallback), and before a human report. Arrivals
  during a drain wait for the next one. Critical sections you finish first:
  authoring a brief, a stack operation, a conflict decision, writing a gate,
  updating `ledger.tsv` or `frontier.json`.
- Each drain classifies every pointer (landed, needs-verify, failed, zombie,
  noise), writes the rows, regenerates `status.md`, then spawns the next wave in
  one message. Account for every spawned child: arrived, respawned, or its scope
  explicitly absorbed. Silently redoing a missing child's work hides the wasted
  spend and the coverage gap.
- A drain turn ends with three lines: counts by state, what changed, gates open.

## Stack safety

- The frontier is computed, never narrative. Recompute `frontier.json` from the
  stacking tool after every merge and stack mutation: ordered PR list, branch
  names, head SHAs, a generation number, the lowest unmerged PR. Forge base refs
  drift mid-restack while the tool's own tracking stays authoritative, so
  resolve it in the stacker's clone.
- Exactly one stacker per stack may run the stacking tool, serialized within its
  stack; record the holder in `preferences.md`. Workers never rebase and never
  run it. PR closes and retargets go through the stacker only, because closing a
  base PR orphans every chain above it. Merges and stack surgery are units with
  briefs.
- Babysitters follow `roles/babysit.md`, one per stack, scoped to one immutable
  frontier generation; they report conflicts to the stacker rather than
  restacking. One retro watcher follows merged PRs for reverts, post-merge CI
  breaks, and orphaned follow-ups.

## Verification

Scale verification to the unit. When VERIFY is one cheap command, the worker
runs it and reports the output and you spot-check receipts. A dedicated verifier
is for verification that is expensive, judgment-laden, or high-blast-radius; one
whose whole product is rerunning a command is ceremony.

`ledger.tsv` holds one row per verdict, keyed by PR number plus head SHA:
`live-ui-verified | unit-test-verified | type-check-only | verifier-blocked |
verifier-failed`. CI green is an input to a verdict, not a verdict. Behavioural
work needs better than `type-check-only`. `verifier-blocked` is not a pass;
respawn when the environment heals. `verifier-failed` gets a fix unit, not a
re-verify. A worker may self-report; a verifier overrides it on the same key. A
new head SHA voids the row, so re-verify after restack.

Externalize a unit's output the moment it lands, never batched to the end of the
run: the worker pushes its branch, the verifier writes its ledger row, receipts
land in the store. Work that exists only on one machine when that machine dies
was never done.

## Liveness and failure

- Never resume an agent to check on it; a resume restarts an idle agent. Probe
  read-only: `ledger.tsv`, `units.tsv`, `gh`, pushed branches. Transcript mtime
  is not liveness. A silent death gets a synthetic postmortem row in `inbox/`
  (unit, failure mode, last evidence, options). Replan on evidence as it
  arrives; never wait for full quiescence.
- Retry by mode: cap-hit or oom, respawn smaller; network drop, retry as-is;
  tool error, retry on a different model; unknown, retry once. Two retries, then
  abandon the unit and replan around it. Bloated or scope-changed child ->
  `rotate-agent` or a fresh spawn with consolidated scope, never a resume-chain.
- A zombie returning hours late reconciles against the current frontier and
  ledger before anything is accepted. Salvage unique findings through a fresh
  unit, never a blind merge.
- When continued spawning would produce garbage tree-wide (bad upstream output,
  broken acceptance, dead infra), write a stop line at the top of
  `preferences.md`, let in-flight work finish, fix the cause, clear it.
- Bound your own infra retries as you bound a child's. After a few consecutive
  tool aborts, `handoff` to durable state (what is done, where it lives, the
  exact command to resume) and end the run. Your own context filling ->
  `handoff` too.
- After a harness restart: local agents are dead, remote work is not. Re-read
  `preferences.md` and `units.tsv`, recompute the frontier, reattach remote work
  by PR and branch rather than agent id, respawn one sub-coordinator per track
  from its stored brief plus current state, drain, resume.

## Escalation

Reaches the human, batched into the status page rather than per item:
irreversible actions (force-push to shared branches, deploys, deletions, closing
someone else's PR), genuine product or preference calls no experiment settles, a
standing order that contradicts observed reality, a program-level dead end that
survived a replan. Park each in `gates.md` before asking, and route work around
it.

Never reaches the human: frontier nudges, restack mechanics, retries, CI flake
triage, review-thread triage, format fixes, scope the brief already forbids
(refuse and continue), and "should I keep going". When in doubt, act and log;
deferring is the measured failure mode. Mid-run discoveries fix only what blocks
the frontier; everything else parks in follow-ups, because at this fan-out a
small scope leak multiplies into PRs nobody asked for.

**Reply:** at checkpoints and close: the predicate and the count against it from
`units.tsv` and `ledger.tsv`, tracks and what each landed, the frontier (PR list
plus SHAs), verdicts summary, what was abandoned and why, gates awaiting the
human (the only asks), the store path, and the trail path. Numbers from the
tables, not narrative. Include PR links.
