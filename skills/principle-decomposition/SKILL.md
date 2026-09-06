---
name: principle-decomposition
description: Use the moment a brief lands in your hands, before the first tool call, and whenever you are about to write a brief for someone else. Also use when a unit comes back partial, when one brief looks like it holds two kinds of work, and when you are tempted to fan a single artifact out across several agents. Decides whether the job is one unit you do yourself or a split you delegate, and bounds how far a split may spread.
---

# Decomposition

Every agent sizes its own work; nobody plans the tree up front.

## Pattern

- **Unit test.** One artifact, one verify command, one kind of work (read,
  build, test, review, research, locate). All three yes -> do it. Any no ->
  split.
- **Split, then delegate.** Cut into units, spawn one agent per unit, roll
  their REPORTs into yours. You orchestrate your subtree; children obey the
  same rule.
- **One unit's worth yourself, the rest delegated.** Never hold two, never
  hand away the one you could finish.
- **Depth is discovered.** A child splits again if its own brief fails the
  test. No depth limit, no plan of the tree.

## Anti-sprawl

Worst failure: agents spawning agents nobody needed.

- **Seams only.** Different artifact, different verify command, different
  kind of work. Never split one artifact by size.
- **Fewest pieces.** More than about three siblings means the brief is a
  program, not a unit. Report it upward with your cut, do not fan out.
- **A handful of tool calls is not a unit.** Do it inline.
- **No pass-throughs.** A child that only re-delegates what it received is a
  layer; delete it.
- **A spawn costs a full brief plus a fresh context.** Brief longer than the
  work -> do the work.
- **Parallel siblings only when independent.** Dependent work chains as fresh
  spawns.

## Overrun

Partial return is information. The RESUME line says what did not land; re-cut
the remainder into new units. Never re-spawn the same brief bigger, never
grant a unit more room. Overruns as a habit mean this text is wrong. Fix the
text.

## Anti-pattern

No call ceilings, no token budgets, no numbers. No script, hook, or watcher
sizes work; sizing is the agent's judgment when the brief lands. Do not fix a
bad cut by enlarging a brief. Do not plan the tree before the first unit runs.
