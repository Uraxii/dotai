---
shape: playbook
---

# Build <feature>

Use for "<user words>". Not for a defect; see diagnose-loop.
The deliverable is working code for <feature> that passes a real check.

1. Name the data shape <feature> needs. Expect one type or schema.
2. Give a worker the goal, the files in scope, and the done check.
3. Wait until the worker reports, at most <time>. Then read its diff.
4. Verify on <real surface>: use <feature> as a user does. A proxy is not a
   pass.
5. Ask a reviewer who did not write the code to check it against <criteria>.
6. If the review finds a defect, go back to step 2, at most 2 times. After
   that, escalate with the findings.

Done when step 4 passes and the review has no open finding.

**Reply:** what was built, verify evidence, review result.
