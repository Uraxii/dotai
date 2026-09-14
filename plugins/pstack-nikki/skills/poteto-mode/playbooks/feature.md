# Feature

Pick when: new or changed behaviour. You own the design. Plan, review,
verify. Delegate implementation; stay in the lead. Owner only: the main
thread or an `orchestrator`. A `developer` handed this playbook returns the
brief unstarted, asking for an `orchestrator`.

1. `how` over the affected subsystem.
2. `architect` for parallel design exploration. Skipping stays as
   `architect skipped: <reason>`; do not fold the design decision
   silently into implementation.
3. Write the throughput checkpoint as four todo items. A dimension that
   genuinely does not apply (single file, no fan-out) keeps its item with
   `n/a: <reason>` rather than being dropped:
   - **Blocking first steps.** Gates run before fan-out.
   - **Independent workstreams.** Disjoint files, services, or layers
     parallelize. Shared writes serialize.
   - **Shared mutable state.** Default to splitting the target
     (`principle-code-quality`). Serialize only for real invariants.
   - **Smallest safe decomposition.** If one worker is best, name why.
4. Delegate code-writing to a developer (`developer-codex` first on Claude
   Code, per SKILL.md) with a specific scope: file
   paths, the named data shape and its organizing structure per
   `principle-code-quality` (a state machine over scattered booleans, a table
   or registry over branching, a typed model over repeated shape assumptions,
   chosen before the delegate writes logic), and success criteria. Review its
   diff yourself. Implementation admits multiple valid shapes (error handling,
   abstraction layer, test structure) -> delegate via `arena` instead, so the
   runners surface the alternatives and the cross-judge guards the pick.
   Mandatory: no skip-with-reason escape, and the laziness rule does not
   override it (the gain is review separation, not lines saved). "The app is
   small" is wrong, and an `orchestrator` leading this playbook spawns its
   developers like the main thread does. Each developer brief carries one unit
   and the worker OWNER line from `references/brief.md`: the developer spawns
   no reviewer, runs no `interrogate`, and opens no PR; you do. Comments per
   `principle-code-quality`. Surgical edits; re-ground against the source for
   upstream-derived files. Port shared-primitive improvements to all consumers
   and verify each. Commit liberally.
5. Verify on the matching surface. "Inconclusive" or wrong-surface is not a
   pass; flag it.
6. Rebase into small, ordered commits; stack follow-ups. Build, verify, and
   commit each small unit before the next.
7. Design contested -> `interrogate` before shipping.
8. Run Opening a PR (`playbooks/opening-a-pr.md`).

Code-coupled work (one feature, one migration) goes to a single owner with the
checkpoint inline; that owner fans out internally after the blocking phase.
Parent-level fan-out is for slices producing independent artifacts (audits,
cross-subsystem investigations, competing experiments). Rewrite the checkpoint
at phase boundaries; spawn a fresh owner rather than chaining interrupts.

**Reply:** what you built, what you chose and why, open decisions. Tables for
design alternatives.
