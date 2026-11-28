---
shape: playbook
---

# Diagnose <symptom>

Use for "<user words>". Not for a new feature; see build-and-verify.
The deliverable is a root cause with evidence and a fix that holds.

1. Reproduce <symptom>. Expect the same failure in two runs.
2. Record a baseline of <measure> before any change.
3. List candidate causes. Expect each cause to name a check that rules it out.
4. Test one cause with one change. Expect <measure> to move, or not.
5. If <measure> improves, keep the change. Otherwise, revert it.
6. Repeat steps 4 and 5 at most 5 times. After 5, escalate with the results.
7. Verify on <real surface>. Expect the failure from step 1 to be gone.

Done when the step 1 reproduction passes and <measure> beats the baseline.

**Reply:** cause, evidence, fix, baseline and final <measure>.
