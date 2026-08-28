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
6. **Drain, do not poll.** Rules below, section "Drain".
7. **Gate at phase boundaries.** Rules below, section "Verification".
   Non-PASS halts that phase.
8. **Rotate, do not chain.** Subagent bloated or scope changed -> `rotate-agent`
   or fresh spawn with consolidated scope. Resume-chaining drops directives.
   Your own context filling -> `handoff` naming what is done, where it lives,
   exact resume command.
9. **Synthesize here.** Cross-workstream judgment happens on main thread, never
   in another agent. Load `principle-guard-the-context-window`: summaries in, bulk out.

**Reply:** workstreams and their owners, units shipped with SHAs, gate verdicts
with resolutions, blocked units with failure mode, what is still in the queue,
decisions taken and open.

## Verification

Gate before any PR opened or integrated: spawn `subagent` loading
`skeptic-gate` (its description carries the triggers). Serial: one gate, wait,
fix, one FRESH gate. Non-PASS halts delivery.

Verdict pinned to head SHA, recorded as a `show-me-your-work` row:
`verdict=<X> sha=<head> ran=<cmd> resolution=<fix|accepted|open>`. New SHA voids
it. CI green is input to a verdict, not a verdict. Ship only when every unit
has PASS for its current SHA.

## Drain

Account for every child; drain the queue before declaring done. Never resume a
child to check on it, probe read-only. Retry by failure mode (cap or OOM ->
smaller scope, network -> as is, tool error -> other model), two tries, then
BLOCKED naming exactly what stuck.
