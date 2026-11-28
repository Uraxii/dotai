---
shape: playbook
---

# Build <feature>

Use for "<user words>". Not for a defect; see diagnose-loop.
The deliverable is working code for <feature> that passes a real check.

1. Name the data shape <feature> needs. Expect one type or schema.
2. Give a worker the goal, the files in scope, and the done check. Expect
   the worker to restate the done check.
3. Wait until the worker reports, at most <time>. Then read its diff.
4. Verify on <real surface>: use <feature> as a user does. A proxy is not a
   pass.
5. Ask a reviewer who did not write the code to check it and the step 4
   result against <criteria>. Expect a list of findings.
6. If the review has an open finding, go back to step 2. Repeat steps 2 to
   6 at most 2 times, until the review has no open finding. After that,
   escalate with the findings.

Done when the review has no open finding.

**Reply:** what was built, verify evidence, review result.
