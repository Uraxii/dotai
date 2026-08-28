# Autonomous run

Pick when: "going to bed", "run until done", "loop until X". You own the exit
condition. Define done, then drive to it without stopping.

1. State the exit condition as a checkable predicate before iteration one
   (tests green, repro fixed, all N PRs merged, pixel-diff zero). A vague goal
   stalls; a predicate lets you stop.
2. Pick the wake mechanism. An event to watch (CI, a merge, a ref advancing)
   gets a watcher subagent that wakes you on the event, with a long time-based
   heartbeat as fallback. No event -> a fixed-interval heartbeat sized to when
   the result is worth re-checking. Use a recurring run if the harness has one.
3. Each iteration makes the smallest change the evidence justifies, verifies
   it against the predicate, commits if it advanced, discards what did not
   help. Belt-and-suspenders that "might help" gets reverted, not left riding.
   Verify each unit before the next instead of batching checks at the end.
4. Mid-run discoveries are yours. Broken skills, related bugs, flaky
   verifiers, review noise, tooling failure, orphaned follow-ups, fixable
   drift: fix them yourself. Out-of-band fixes get their own PR. Do not park
   reversible work for the human and do not stop to ask
   (`principle-never-block-on-the-human`). Surface only irreversible actions,
   genuine preference calls no experiment settles, or a real dead end. Return
   to the predicate after each side fix.
5. Checkpoint every iteration via `show-me-your-work`: one row for what
   changed and whether the predicate moved. A run with no trail cannot be
   audited or resumed.
6. Stop when the predicate is met. A plateau is not a stop: pivot approach and
   push past it. Surface a genuine dead end rather than spinning, and never
   relax the predicate to declare victory. Stopping early -> `handoff` naming
   what is done, where it lives, and the exact resume command.

**Reply:** exit condition, iterations run, what landed, what was discarded,
final predicate state.
