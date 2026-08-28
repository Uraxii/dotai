# Bug fix

Pick when: reported defect to reproduce, root-cause, and fix with runtime
evidence. Not for new behaviour (Feature) or structure-only change
(Refactoring).

Every shipped line traces to runtime evidence. Belt-and-suspenders that "might
help" is hypothesis, not fix; it does not ship. Evidence refutes hypothesis ->
revert what it motivated.

Copy these steps into todolist verbatim before any task-specific todo.

1. **Reproduce first.** Yourself, on the real surface. Cannot reproduce ->
   cannot verify fix. Capture exact command, input, observed output. Godot
   runtime symptom -> `godot-playtest`. No repro after real attempt -> report
   BLOCKED with what you tried. Never fix blind.
2. **Root-cause.** Subagent loads `diagnose`. Binary-search hypotheses, get
   runtime evidence each pass, eliminate. Null guard silencing a crash is
   symptom fix, not fix. Confirm mechanism with evidence BEFORE designing fix.
3. **Pattern, not instance.** Grep same shape elsewhere. Fix every instance or
   name the ones you leave and why.
4. **Failing test first.** Subagent loads `tdd`. Test fails for stated reason
   before fix exists. No cheap test path -> state why, name runtime evidence
   replacing it.
5. **Fix.** Subagent loads `ponytail` and `code-quality` plus its reference for
   the language in play. `ponytail` is mandatory on any step writing code.
   Smallest change removing the cause. No adjacent refactoring.
6. **Prove it.** Re-run step 1 repro, not proxy. Load `principle-prove-it-works`. Test
   green AND original symptom gone. Verification failed -> suspect observation
   method before system.
7. **GATE.** Subagent loads `skeptic-gate`, serial: one gate, wait, fix, one
   fresh gate. Record verdict, head SHA, and resolution in verdict ledger.
   Non-PASS halts delivery.
8. **Ship.** `yeet`. Stage commits so failing repro lands before fix; diff
   tells story.

**Reply:** root cause in one sentence, repro command, what fix changed,
runtime evidence, other instances of pattern found, gate verdict with SHA.
