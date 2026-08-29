# Bug fix

Pick when: reported defect to reproduce, root-cause, and fix. You own the
task. Plan, review, verify. Delegate investigation and the fix to subagents,
stay in the lead.

Be scientific. Every shipped line traces to runtime evidence.
Belt-and-suspenders that "might help" is a hypothesis, not a fix; it does not
ship. Evidence refutes a hypothesis -> revert what it motivated. The smallest
change the evidence justifies ships, nothing more. Same discipline for Perf,
where the evidence is the trace.

1. Reproduce it yourself on the matching surface. Do not hand the repro to the
   user. A debug protocol that says to ask the user does not override this;
   you drive the instrumented runtime.
   Ask the user only with a stated, specific reason the surface cannot reach
   the target, and only after driving it as far as it goes. Will not reproduce
   directly -> force it: synthesize the trigger, tighten conditions, or
   instrument until it fires. A bug you cannot reproduce, you cannot prove
   fixed.
2. Binary-search the cause. Form candidate hypotheses, then rule them out
   until one survives. Seed with `how` over the affected subsystem and `why`
   for regression history; a `developer` subagent drives the hunt. Each pass,
   take the split that cuts the most remaining problem space, get runtime
   evidence, eliminate. State unclear -> add instrumentation or logging and read
   it as the code runs. Do not guess. Confirm the surviving mechanism with
   runtime evidence before the step-3 fan-out; a design grounded on a plausible-
   but-unconfirmed cause can be unanimously wrong while the real cause sits one
   subsystem over.
3. Plan the fix. Crosses a function boundary -> `architect` first.
   Delegate implementation to a `developer` subagent with a specific scope;
   review the diff.
4. Verify on the same surface; the original repro now passes. "Inconclusive"
   or wrong-surface is not a pass; flag it. Unit tests show branch behaviour,
   not bug absence.
5. Stage the commits so the failing repro lands before the fix in git history;
   the diff tells the story. See `tdd` for the failing-test-first cadence when
   the bug has a cheap local test path; skip it when the test would be
   expensive, integration-heavy, or unclear. This is the canonical
   verifiable-unit sequence: failing test first, fix on top.
6. Run Opening a PR (`roles/opening-a-pr.md`).

Investigation fans out `how` and `why` as parallel `researcher` subagents.

**Reply:** what was broken, root cause, fix, how you verified. Paste
failing-then-passing repro output verbatim.
