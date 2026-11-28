---
shape: playbook
---

# <Change name>

Use for "<user words>". Not for <near miss>; see <other playbook>.
The deliverable is <changed system state>, not a plan for it.
Read each step before you do it, and do the steps in order.

1. Save the current state of <target> to <backup path>. Expect the copy to
   exist and to match <target>.
2. Run <command> as a dry run. Expect the diff to touch only <scope>.
3. Pause. Show the dry-run diff and ask <owner> to approve the change.
4. Run <command>. Expect <observable state>.
5. If step 4 fails, restore the copy from step 1, then stop and report.
6. Verify on <real system>: <check>. A proxy is not a pass.

Done when <check> passes on <real system>.

**Reply:** what changed, dry-run diff, who approved, verify result.
