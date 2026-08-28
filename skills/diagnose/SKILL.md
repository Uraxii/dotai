---
name: diagnose
description: Diagnosis loop for hard bugs and performance regressions. Use when the user says "diagnose"/"debug this", or reports something broken/throwing/failing/slow.
---

# Diagnosing bugs

Skip a phase only when you say why.

## Phase 1: feedback loop

**This is the skill.** Everything else is mechanical. With a tight pass/fail
signal that goes red on *this* bug you will find the cause; bisection,
hypotheses, and instrumentation all just consume it. Spend the effort here.

Ways to construct one, roughly in order:

1. Failing test at whatever seam reaches the bug.
2. Curl or HTTP script against a running dev server.
3. CLI invocation on a fixture input, diffed against a good snapshot.
4. Headless browser script asserting on DOM, console, or network.
5. Replay a captured trace through the code path in isolation.
6. Throwaway harness: minimal subset, mocked deps, one call that hits the bug.
7. Property or fuzz loop, for "sometimes wrong output".
8. Bisection harness, so `git bisect run` can drive it.
9. Differential loop: same input through two versions or configs, diff output.
10. HITL bash script, last resort: drive the human with
    `scripts/hitl-loop.template.sh` so the loop stays structured.

**Tighten it.** Treat the loop as a product: faster (cache setup, narrow
scope), sharper (assert the specific symptom, not "didn't crash"), more
deterministic (pin time, seed RNG, isolate filesystem, freeze network). For a
non-deterministic bug the goal is not a clean repro but a higher reproduction
rate: loop the trigger 100x, parallelise, add stress, inject sleeps. 50% flake
is debuggable, 1% is not.

**Cannot build one:** stop and say so. List what you tried, ask for
environment access, a captured artifact (HAR, log or core dump, recording), or
temporary production instrumentation. Never hypothesise without a loop.

**Done when** you can name one command, already run once (paste it and its
output), that is red-capable (drives the actual bug path and asserts the user's
exact symptom, not "runs without erroring"), deterministic, fast, and runnable
unattended. Reading code to build a theory before that command exists: stop.

## Phase 2: reproduce and minimise

Run the loop, watch it go red. Confirm it produces the failure the **user**
described and not a nearby one, that it repeats across runs, and that you
captured the exact symptom for later phases to verify against.

Then shrink to the smallest scenario that still goes red: cut inputs, callers,
config, data, steps one at a time, re-running after each cut. Done when
removing any remaining element turns the loop green. The minimal repro shrinks
the Phase 3 hypothesis space and becomes the Phase 5 regression test.

## Phase 3: hypothesise

Generate 3-5 ranked hypotheses before testing any; one hypothesis anchors on
the first plausible idea. Each must be falsifiable, stating its prediction ("if
X is the cause, changing Y makes the bug disappear"). No prediction means a
vibe: discard or sharpen it. Show the list to the user, who often re-ranks it
instantly, but proceed if they are AFK.

## Phase 4: instrument

Each probe maps to one Phase 3 prediction. Change one variable at a time.
Debugger or REPL first, one breakpoint beats ten logs, then targeted logs at
the boundaries that distinguish hypotheses. Never "log everything and grep".
Tag every debug log with a unique prefix (`[DEBUG-a4f2]`) so cleanup is one
grep. For perf regressions logs are usually wrong: baseline first, then bisect.

## Phase 5: fix and regression test

Write the regression test before the fix, but only if a **correct seam** exists
for it: one where the test exercises the real bug pattern as it occurs at the
call site. A too-shallow seam gives false confidence. **No correct seam is
itself the finding**, so note it. With a correct seam: turn the minimised repro
into a failing test, watch it fail, fix, watch it pass, then re-run the Phase 1
loop against the original un-minimised scenario.

## Phase 6: cleanup and post-mortem

Before declaring done: original repro no longer reproduces, regression test
passes (or the absent seam is documented), all `[DEBUG-...]` instrumentation
removed, throwaway prototypes deleted, and the hypothesis that proved correct
stated in the commit or PR. Then ask what would have prevented this bug; an
architectural answer (no test seam, tangled callers, hidden coupling) gets
named with specifics, **after** the fix lands.
