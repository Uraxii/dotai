# Refactoring

Pick when: behaviour-preserving structural change. Rename, extract, inline,
dedupe, move, restructure. Structure changes, behaviour does not.

Refactor smuggling a behaviour change loses its safety net. Cleanup revealing a
missing feature or real bug -> split out, ship structural change first. New
requirement landing on the old shape -> `principle-redesign-from-first-principles`, then
route to Feature.

Copy these steps into todolist verbatim before any task-specific todo.

1. **Green baseline.** Run suite before touching anything; record command and
   pass count. Preserved means proven preserved. No coverage over target ->
   characterization test first, subagent loads `tdd` or
   `test-automation-engineer`, pinning current behaviour, bugs included. Type
   check and lint are not a pin.
2. **Name the smell.** Subagent loads `code-quality`, cites the Fowler smell plus
   naming rules for any rename. "Felt messy" is not a reason -> stop, report
   NO-OP.
3. **Delete before you construct.** Load `principle-laziness-protocol`. Dead code, unused
   params, speculative abstraction, reinvented stdlib. Subtract, re-run green,
   then reshape the simpler base. Half the planned refactor often vanishes here.
4. **Name the target shape.** `codebase-design` for seams. State what module
   layout, types, and call graph should be if built today. Reshape must delete
   branches or invalid states, not add indirection.
5. **One transform, one green check.** Subagent loads `ponytail`, mandatory on
   any step writing code. Apply single transform, run suite, commit. Never
   batch several then verify once. Red -> revert that transform, do not patch
   forward.
6. **Migrate callers and delete old path in same change.** No shim, no
   deprecated alias, no re-export for internal callers. Rename lands everywhere
   at once: code, tests, diagrams, docs, comments, issue text. Spot-check every
   rename against real files; strings and prose get missed.
7. **No behaviour smuggled in.** Real bug spotted mid-refactor -> leave it, say
   so, file it as separate unit. Silent fix makes diff unreviewable.
8. **Prove equivalence.** Load `principle-prove-it-works`. Script diffing old vs new
   output, replayed baseline, or smoke run on real surface. Not "it compiles",
   not a delegate's "looks good". Confirm reader load dropped: fewer layers,
   less hidden state. No drop anywhere -> revert.
9. **GATE.** Subagent loads `skeptic-gate`, serial: one gate, wait, fix, one
   fresh gate. Record verdict, head SHA, resolution as a `show-me-your-work` verdict row. Then
   `yeet`.

**Reply:** named smell, baseline command with before/after pass counts,
transforms in order, what was deleted outright, confirmation every caller moved
and no shim remains, reader-load delta, bug deferred and where filed, gate
verdict with SHA. No new behaviour.
