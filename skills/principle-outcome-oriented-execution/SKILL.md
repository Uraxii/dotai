---
name: principle-outcome-oriented-execution
description: Use during a planned rewrite, port, or migration with explicit phases, when tempted to add shims, adapters, dual code paths, or flags purely to keep every intermediate commit green. Converges on the target architecture and proves correctness at phase boundaries instead of at every step.
---

# Outcome-oriented execution

Optimise for the intended, verifiable END state. Not for smooth intermediate
states.

**Why:** keeping every step fully stable breed temporary compatibility code:
shim, adapter, dual code path, flag nobody ever remove. Temporary become
long-lived debt. Converge on target architecture, prove correctness at explicit
verification boundary.

## Core rule

- End-state integrity beat transitional stability.
- Intermediate breakage acceptable when planned, scoped, reversible.
- Full verification before declaring done. Always.

## Guardrails

- Only for planned rewrite or migration with explicit phase boundary. Not for
  ordinary feature work on a live system.
- Declare up front WHERE breakage is acceptable and for how long. Write it in
  the plan.
- Keep high-signal checks running on the area being touched while migrating.
- Require full static and runtime verification at plan completion.
- "Reversible" must be real: branch, backup, exported original asset, infra
  state snapshot. No safety net -> not this principle, go incremental.
- Cut over once and delete the old path in the same phase. Not both stacks live
  "just in case".
