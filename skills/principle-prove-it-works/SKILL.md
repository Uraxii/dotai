---
name: principle-prove-it-works
description: Use right before declaring a task done or reporting success, and when checking work a delegate says it finished. Requires observing the real artifact (run the scene, render the image, hit the endpoint, read the diff) instead of trusting a green build, a file timestamp, or an agent's own summary.
---

# Prove it works

Verify every output against real thing. No proxy, no self-report, no
"it compiles". Unverified work has unknown correctness. Indirect check (mtime,
cached screenshot, one log line, agent summary) feel cheaper than direct
observation; acting on wrong inference cost far more.

After every task ask: how do I prove this actually work?

- Process alive -> query process, not derived state file.
- Value correct -> read actual value at runtime, not cached or derived copy.
- Verification fail -> suspect observation method BEFORE suspecting system.

## Full chain

Build (necessary, never sufficient), then exercise the real path as the
consumer would, from outside the thing, and follow the chain input -> output
with no gap trusted.

**Delegation.** Trust artifacts, not reports. Inspect diff, file content, runtime behaviour.
Agent report what it INTENDED, not always what happened.

## Script the check

Strongest proof = deterministic script re-running same comparison, not one-time
eyeball. Write script, run it, keep output as artifact reviewer can rerun.
Script diffing old vs new output catch what glance miss. Keep artifact visible
to human; commit only when trail must stay auditable later, like big port or
migration.
