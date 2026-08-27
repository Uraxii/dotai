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
- The brief is the product. Vague brief fails quietly; worker cannot ask you.

Copy these steps into todolist verbatim before any task-specific todo.

1. **Split into workstreams.** One workstream = one coherent body of work with
   its own branch. Each gets one `worker` loading `tech-lead` (software) or
   `art-director` (art), spawned in background so main thread stays live. Art
   workstream brief carries FORBIDDEN "never load image pixels, relay contact
   sheet URLs only".
2. **Load the queue into bd.** `agent-workbench` bd. One unit is one commit
   worth of work carrying its own verification. Record dependencies so ready
   queue drives order. Record program plan in kb.
3. **Write briefs, not instructions.** Full spawn contract per unit, per the
   orchestration skill. Sibling worker output that a unit depends on gets
   pasted into its CONTEXT in full; subagents cannot see siblings.
4. **Pin models per call.** `models.md`. Never frontmatter. Never fable, sol,
   or luna without explicit user permission.
5. **Blocking phases before fan-out.** Scaffold, schema, shared contracts land
   first, in one unit, verified, before parallel work starts. Shared writes
   serialize; disjoint paths parallelize.
6. **Drain, do not poll.** Completion is a queue event: note it, keep working.
   Never resume a child to check on it; probe read-only. Account for every
   child spawned before declaring any phase done.
7. **Gate at phase boundaries, serial.** One `skeptic-gate` worker, wait for
   verdict, fix, one fresh gate. Never batch, never parallel. Record verdict,
   head SHA, and resolution in verdict ledger. Non-PASS halts that phase.
8. **Rotate, do not chain.** Worker bloated or scope changed -> `rotate-agent`
   or fresh spawn with consolidated scope. Resume-chaining drops directives.
   Your own context filling -> `handoff` naming what is done, where it lives,
   exact resume command.
9. **Synthesize here.** Cross-workstream judgment happens on main thread, never
   in another agent. Load `guard-the-context-window`: summaries in, bulk out.

**Reply:** workstreams and their owners, units shipped with SHAs, gate verdicts
with resolutions, blocked units with failure mode, what is still in the queue,
decisions taken and open.
