---
name: setup-models
description: The user invokes this by name to change which model each delegated role runs on. Interviews them role by role, then rewrites the orchestration skill's model map so later spawns pin the new choices.
---

# Setup models

Rewrite the orchestration skill's `models.md`, the per-role model map. Skills
and playbooks read it and pin `model` per Agent call. Absent role -> child
inherits parent.

Target: the `orchestration` skill's model map, `models.md`, bundled beside its
SKILL.md. Locate it through the same skills install this skill was loaded
from; never hardcode an install layout or guess a home directory.

Allowed values: `sonnet`, `opus`, `haiku`, `fable`, where `fable`, `sol`,
and `luna` are NEVER assigned without explicit user permission.

## Steps

### 1. Load current state

Read the target file. Its table is the current choice. Missing file -> start
from defaults: opus for architect-designer, skeptic-gate, tech-lead;
sonnet for art-director, implementation-specialist, requirements-clarifier,
test-automation-engineer; haiku for big-pickle-simple-tasks.

### 2. Interview

Show every role with its current model. Ask whether to accept as-is or change
specific roles. Offer the four allowed values plus `inherit` (role omits
`model`, runs on parent's). Prefer the harness's structured question prompt over free text where one exists.

Rough shape: opus for judgment, design, and gates. Sonnet for scoped
execution. Haiku for mechanical decomposition. Offer that as the default, not
as a lecture.

### 3. Validate

Reject any value outside the allowed set plus `inherit`. Map pointing at a
model the user cannot run breaks every delegation reading it.

`fable` needs explicit user permission in this turn, stated in words, before
it may be written. Same for any sol or luna role. Silence is not permission.
No permission -> leave that role unset and say so.

### 4. Write

Overwrite the whole file so re-runs stay idempotent. Keep its shape: the
`setup-models rewrites this file` note at top, the allowed-values line with
its permission caveat naming fable, sol, and luna, one table row per role, the
inherit rule, the fable hard rule.

### 5. Confirm

Tell the user the file path written and that it applies to spawns from now on.
Re-running this skill updates it.
