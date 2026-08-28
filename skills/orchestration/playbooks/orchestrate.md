# Orchestrate

Pick when: program outlives any single agent. Many units, several workstreams,
stacked PRs, human checking in twice a day. One task driven to a predicate is
not a program: route to its own playbook plus `autonomous-run`.

Ceremony scales with program. Work one agent finishes in one session pays this
tax for nothing. Below that line, do not pick this.

You own the program, never the code. Author briefs, drain the queue, decide.
Three rules carry the rest:

- Completions are queue events, not interrupts.
- Every spawn carries standing orders verbatim.
- The brief is the product. Vague brief fails quietly; subagent cannot ask you.

Copy these steps into todolist verbatim before any task-specific todo.

1. **Split into workstreams.** One workstream = one coherent body of work with
   its own branch. Each gets one `subagent` loading `tech-lead` (software) or
   `art-director` (art), spawned in background so main thread stays live. Art
   workstream brief carries FORBIDDEN "never load image pixels, relay contact
   sheet URLs only".
2. **Load the queue into bd.** `agent-workbench` bd. One unit is one commit
   worth of work carrying its own verification. Record dependencies so ready
   queue drives order. Record program plan in kb.
3. **Write briefs, not instructions.** Full spawn contract per unit, per the
   orchestration skill. Sibling subagent output that a unit depends on gets
   pasted into its CONTEXT in full; subagents cannot see siblings.
4. **Pin models per call.** `models.md`. Never frontmatter. Never fable, sol,
   or luna without explicit user permission.
5. **Blocking phases before fan-out.** Scaffold, schema, shared contracts land
   first, in one unit, verified, before parallel work starts. Shared writes
   serialize; disjoint paths parallelize.
6. **Drain, do not poll.** Rules below, section "Drain and liveness".
7. **Gate at phase boundaries.** Rules below, sections "Before shipping" and
   "Verdict ledger". Non-PASS halts that phase.
8. **Rotate, do not chain.** Subagent bloated or scope changed -> `rotate-agent`
   or fresh spawn with consolidated scope. Resume-chaining drops directives.
   Your own context filling -> `handoff` naming what is done, where it lives,
   exact resume command.
9. **Synthesize here.** Cross-workstream judgment happens on main thread, never
   in another agent. Load `principle-guard-the-context-window`: summaries in, bulk out.

**Reply:** workstreams and their owners, units shipped with SHAs, gate verdicts
with resolutions, blocked units with failure mode, what is still in the queue,
decisions taken and open.

## Before shipping

Gate required before any PR opened or integrated, in this program and in every
playbook that reaches for a gate. Spawn `subagent` loading `skeptic-gate`. Any
ONE trigger is enough:

- Architecture change.
- Security or trust-boundary change.
- Netcode, shared state, or replication change.
- Migration.
- Public API or schema change.
- Large cross-cutting change.
- Verification weak or missing.
- Tests passed but result looks suspicious.

Serial rule: spawn ONE gate. Wait for verdict. Fix. Spawn ONE FRESH gate.
Never batch, never parallel. Gate calls are a dependency chain, not
independent tool calls. Non-PASS verdict halts delivery until resolved.

## Verdict ledger

Verdict pinned to commit SHA, never to memory or transcript. Record every gate
verdict AND its resolution as bd note on tracking issue via `agent-workbench`:
`verdict=<X> sha=<head> by=skeptic-gate ran=<cmd> resolution=<fix|accepted|open>`.

- New head SHA voids verdict. Re-gate after any commit, rebase, amend.
- CI green is input to verdict, not verdict.
- BLOCK gets fix task, not re-gate of same SHA.
- Before shipping: every change on branch has PASS for current SHA.
- `show-me-your-work` trail active -> gate verdict also goes in as a row on
  that trail, not just the bd note.

## Drain and liveness

- Never resume child just to check on it. Resume restarts an idle agent.
  Probe read-only instead.
- Account for every child spawned. Completion is queue event, not interrupt;
  note it, keep working, drain queue before declaring done. Unaccounted child
  is unfinished work.
- Retry by failure mode, never blindly. Cap-hit or OOM -> respawn smaller
  scope. Network -> retry as is. Tool error -> different model. Unknown ->
  once.
- Bound own retries: two, then mark unit blocked and replan around it.
  Cannot replan -> bubble up BLOCKED naming exactly what stuck.
