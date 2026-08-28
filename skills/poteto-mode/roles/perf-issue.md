# Perf issue

Pick when: one-off performance regression to measure and fix. You own the
measurement story. Plan, review, verify the numbers. Tie every fix to a
measurement; do not read source instead of measuring.

1. Capture a baseline trace on the matching surface.
2. `how` to ground hypotheses; do not claim a perf ceiling without running it
   first. Most fixes come from eight strategy families. Use them as hypothesis
   generators, not a checklist. A family earns an attempt only when the trace
   shows the signal it names, and a focused fix for the dominant cost beats
   applying all eight.
   - **Elimination.** Cheapest work is work that does not run. Before
     optimizing the hot path, ask whether it needs to exist: a computation
     nobody consumes, a feature gate always off for this user, a redundant
     sync, a legacy path kept "just in case". The trace shows what is slow,
     never that it is deletable, so this family needs the `how` pass, not the
     profiler. Deleting the work beats every other family when it applies.
   - **Divide and conquer.** Dominant cost scales with input size. Split the
     work so each piece touches less (chunk, shard, prune the search space) or
     so independent pieces run in parallel.
   - **Caching.** Same computation or fetch repeats on identical inputs. Store
     and reuse; name what invalidates it before claiming the win.
   - **Indirection.** Hot path does expensive work a cheaper intermediate
     could absorb: an index instead of a scan, a queue shifting work off the
     interactive thread, a handle letting a cheaper implementation swap in.
     Add the hop only when it removes more from the critical path than it
     adds; a layer sitting on the hot path without removing work is pure cost.
   - **Batching.** Many small operations each pay a fixed overhead (RPC,
     query, syscall, draw call). Coalesce to pay it once per batch.
   - **Redundancy.** The wait hangs on one slow instance or attempt. Duplicate
     the work (replicas, hedged requests, speculative execution) and take the
     fastest result. Trades load for tail latency, so the trace has to show
     the wait dominates and the system has headroom.
   - **Lazy evaluation.** Cost lands on results never used or not needed yet
     (eager init on the boot path, rendering offscreen items). Defer until
     first use.
   - **Scheduling.** The work must happen, but not during the interactive
     moment. Move it where nobody waits: idle callbacks, background warmup
     after boot, precompute before the user arrives, cleanup after the frame
     commits. Distinct from Lazy: Scheduling often runs the work earlier, or
     in the hot moment's shadow. The win is perceived latency, so measure the
     interactive path, not total work done.
3. Plan the fix from the trace. Crosses a function boundary ->
   `architect-designer` first. Delegate implementation to a `developer`
   subagent; review the diff. Capture a post-fix trace. Verify each attempt
   before trying the next.
4. Parse and compare the artifacts (JSON to sqlite, diff). "Inconclusive" or
   wrong-surface is not a pass; flag it.
5. Cite the measurement in the PR.
6. Run Opening a PR (`roles/opening-a-pr.md`).

Sustained improvement against a metric rather than a one-off fix -> Hillclimb
(`roles/hillclimb.md`).

**Reply:** baseline number, post-fix number, delta, artifact path.
