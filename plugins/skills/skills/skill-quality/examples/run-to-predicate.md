---
shape: playbook
---

# Run <task> to <predicate>

Use for "run until <predicate>". Not for one fix; see diagnose-loop.
The deliverable is <predicate> holding, with a decision log.

1. Write the stop predicate as a check: <command>. Expect it to fail now.
2. Open a decision log at <log path> with four columns: what, why,
   evidence, result.
3. Do the next unit of work. Expect the check to move toward a pass.
4. Log the decision. Write the current state to <checkpoint path>.
5. If the check passes, go to step 7.
6. Repeat steps 3 to 5 at most <N> times. After <N>, escalate to <owner>
   with the log.
7. Verify the predicate on <real system>.

Done when <command> passes on <real system>. Do not relax the predicate.

**Reply:** predicate result, units done, log path, checkpoint path.
