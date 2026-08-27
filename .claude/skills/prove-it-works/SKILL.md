---
name: prove-it-works
description: Use right before declaring a task done or reporting success, and when checking work a delegate says it finished. Requires observing the real artifact (run the scene, render the image, hit the endpoint, read the diff) instead of trusting a green build, a file timestamp, or an agent's own summary.
---

# Prove It Works

Verify every output against real thing. No proxy, no self-report, no
"it compiles".

**Why:** unverified work has unknown correctness. Indirect check (mtime,
cached screenshot, one log line, agent summary) feel cheaper than direct
observation. Acting on wrong inference cost far more than checking source.

After every task ask: how do I prove this actually work?

## Check real thing

- Process alive -> query process, not derived state file.
- Value correct -> read actual value at runtime, not cached or derived copy.
- Verification fail -> suspect observation method BEFORE suspecting system.

## Full chain

1. Build. Necessary, never sufficient.
2. Exercise real path, as consumer would.
3. Follow chain input -> output, no gap trusted.

Domain shapes:

- Godot: run headless, step frames, read runtime state. "Scene loads" is not
  "feature works".
- Art pipeline: render one image with final params, open it, look. Prompt
  accepted != image correct.
- Infra: hit service through real ingress path, not localhost inside
  container.
- Library or API: call from outside the package, as caller does.

## Delegation

Trust artifacts, not reports. Inspect diff, file content, runtime behaviour.
Agent report what it INTENDED, not always what happened.

## Script the check

Strongest proof = deterministic script re-running same comparison, not
one-time eyeball. Write script, run it, keep output as artifact reviewer can
rerun. Script diffing old vs new output catch what glance miss. Keep artifact
visible to human; commit only when trail must stay auditable later, like big
port or migration.
