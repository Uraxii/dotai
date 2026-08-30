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
- Diagnosis is an output too. Read the system's own log and source before
  theorising from config plus plausible mechanism; the system usually names
  its refusal.

## Full chain

Build (necessary, never sufficient), then exercise the real path as the
consumer would, from outside the thing, and follow the chain input -> output
with no gap trusted.

**Delegation.** Trust artifacts, not reports. Inspect diff, file content, runtime behaviour.
Agent report what it INTENDED, not always what happened.

## Watch the check fail

Guard never seen failing prove nothing. Before trusting any check (lint,
verify script, monitoring probe, CI gate, review pass), feed it one
known-bad input and watch it go red. Only then trust its green.

- New or changed guard -> negative control first: the EICAR file, the
  planted syntax error, the downed target, the rejected API response.
- Reviewing a diff -> run the linter on it. Eyeball catch style, not defect.
  No linter cover the defect class -> that gap is itself a finding.
- Check that cannot fail is worse than no check: it manufacture confidence
  and schedule its own discovery for the outage.

## Script the check

Strongest proof = deterministic script re-running same comparison, not one-time
eyeball. Write script, run it, keep output as artifact reviewer can rerun.
Script diffing old vs new output catch what glance miss. Keep artifact visible
to human; commit only when trail must stay auditable later, like big port or
migration.
