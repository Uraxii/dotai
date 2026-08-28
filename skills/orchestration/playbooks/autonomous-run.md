# Autonomous run

MODIFIER, not a standalone sequence. Layers on top of one of the five
playbooks (bug-fix, investigation, feature, refactoring, orchestrate). Pick the
base playbook first, copy its steps, then add these on top.

Apply when: long task driven unattended, no human awake to unblock it. "Going
to bed", "run until done", "loop until X".

Copy these steps into todolist verbatim, after the base playbook's steps.

1. **State the done predicate.** Countable: N issues closed, suite green, zero
   occurrences left, repro fixed. "Until it is good" is not a predicate. Cannot
   count it -> do not start, ask instead.
2. **Fix the stop list before unit one.** Irreversible actions still stop:
   force-push to shared branch, deploy, data deletion, anything sent to a
   person. Everything reversible proceeds without asking. Load
   `principle-never-block-on-the-human`.
3. **Close each unit before opening next.** Run its check now, commit and push
   or advance the bd item immediately. Never batch state or verification to the
   end. Work existing only in this session's context was never done; an
   unverified unit poisons every unit after it.
4. **Park questions, route around them.** Write question plus the default you
   are taking into bd, take the reversible option, keep going. Never block on
   an answer arriving in the morning.
5. **Checkpoint every iteration.** One bd row: what changed, whether predicate
   moved. Run with no trail cannot be audited or resumed.
6. **Smallest change the evidence justifies.** Advanced -> commit. Did not help
   -> discard, do not leave it riding.
7. **Retry by failure mode, bound yourself.** Cap-hit or OOM -> respawn smaller
   scope. Network -> retry as is. Tool error -> different model. Unknown ->
   once. Two retries, then mark unit blocked in bd and replan around it.
8. **Rotate or hand off, never spin.** Context filling or consecutive tool
   aborts -> `rotate-agent`, or `handoff` naming what is done, where it lives,
   exact resume command, then end run.
9. **Stop only on predicate.** Plateau is not a stop: pivot approach. Genuine
   dead end -> surface it. Never relax the predicate to declare victory. Base
   playbook's gate still runs before finished is claimed.

**Reply:** the predicate and whether met with the count, each unit shipped with
SHA, parked questions with defaults taken, abandoned units with failure mode,
gate verdict, resume command if stopped early.
