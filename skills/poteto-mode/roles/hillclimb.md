# Hillclimb

Pick when: sustained, iterative improvement of one measurable thing against a
target. "Hillclimb on X", "make startup 50% faster", "systematically drive
down <metric>", "keep trying until <metric> improves by N%". A one-off fix is
Bug fix or Perf issue; this is the loop. You own the metric and the
experiment's integrity. Supervise and review; delegate the attempts.

Core discipline: one change, one measurement, keep or revert. Never stack
untested changes, never claim a win from code inspection. The data decides
(`principle-prove-it-works`).

1. Ground the workload and architecture before choosing the ruler. Run `how`
   over the target, name the realistic workload dimensions that can move the
   result (data size, history, state, concurrency), and select a case that
   reproduces the user's complaint. No case reproduces it -> fix the repro
   instead of hillclimbing. Then fix one metric, the direction that counts as
   better, and a checkable stop predicate pairing a target with a floor on
   attempts so a lucky early win cannot end the run ("at least 50% better than
   baseline and at least 10 iterations" is the shape). Use the user's numbers
   when given, otherwise agree them.
2. Build the measurement harness, prove its sensitivity, freeze it
   (`principle-build-the-lever`). Run contrasting realistic workloads and
   confirm the target case reproduces the symptom while easier cases separate
   as expected. Ruler cannot distinguish them -> revise the workload or
   metric. Once frozen, one repeatable command emits the metric, sampled
   enough to clear the noise (median of N, not a single run); changing it
   invalidates every earlier number. Record the baseline metric and a green
   run of the regression gate before any change.
3. Open the decision log via `show-me-your-work`. One row per attempt: id,
   hypothesis, change, before, after, delta, tests, verdict (kept or
   reverted), note. This is the run's memory. Read it before each attempt so
   the search accumulates instead of circling. Keep it out of the tree
   (gitignored) so it survives reverts.
4. Ground each hypothesis in the architecture model from step 1, so it names a
   specific mechanism ("defer X off the boot path because it blocks first
   paint"), not "try memoizing something".
5. Loop, one hypothesis per iteration:
   - Hand the change to a `developer` subagent with a tight scope; supervise
     and review the diff rather than typing it
     (`principle-guard-the-context-window`). Several independent hypotheses
     live -> fan them to parallel subagents, each in its own worktree so they
     cannot collide (`principle-code-quality`).
   - Measure before and after with the frozen harness, and run the regression
     gate.
   - Accept only when the metric moves past noise and the gate stays green.
     Otherwise revert the change in full; a tweak that "might help" does not
     ride along.
   - One commit per accepted fix, staging only the files you changed
     (`git add <files>`, never `-A`). Log the row either way.
   Each iteration ends in a check before the next begins. Unattended run ->
   borrow only the wake mechanism from Autonomous run
   (`roles/autonomous-run.md`), not its stop rule. This role's stop criteria
   govern, so a plateau means pivot, not stop.
6. Push past the first plateau. On a stall, several rejects in a row, pivot
   category, combine near-misses, re-read the source, or try something more
   radical before concluding the hill is climbed. Correctness and simplicity
   outrank the number. Revert a win that breaks behaviour; keep a
   simplification that holds the number (`principle-laziness-protocol`).
7. Stop when the predicate is met, or when the remaining ideas are genuinely
   marginal and not worth their cost. Do not relax the predicate to declare
   victory, and do not quit while cheap untried hypotheses remain. Stuck ->
   surface it instead of spinning.
8. Run Opening a PR (`roles/opening-a-pr.md`) with the accepted commits
   stacked in the order they landed, so the metric's climb reads top to
   bottom.

**Reply:** the metric and target, baseline to final with the percent delta,
iterations run (kept vs reverted), each accepted fix on one line, the decision
log path, and the best idea you would try next if pushed further.
