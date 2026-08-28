---
name: setup-models
description: The user invokes this by name to change which model each delegated role runs on. Interviews them role by role, then rewrites the orchestration skill's model map so later spawns pin the new choices.
---

# Setup models

Rewrite `models.md`, the per-role model map bundled beside the `orchestration`
skill's SKILL.md. Skills and playbooks read it and pin `model` per Agent call.
Role absent from it -> the child inherits the parent's model. Locate the file
through the same skills install this skill was loaded from; never hardcode an
install layout or guess a home directory.

Allowed values: `sonnet`, `opus`, `haiku`, `fable`, plus `inherit`. `fable`,
`sol`, and `luna` need explicit user permission stated in words this turn.
Silence is not permission; no permission -> leave the role unset and say so.

1. **Load current state.** Read the target file; its table is the current
   choice. Missing file -> start from opus for architect-designer,
   skeptic-gate, tech-lead; sonnet for art-director, requirements-clarifier,
   test-automation-engineer; haiku for big-pickle-simple-tasks; `opus, sonnet`
   for the `interrogate reviewers` list, one reviewer per entry, repeats
   allowed.

2. **Interview.** Show every role with its current model and ask whether to
   accept as-is or change specific roles. Prefer the harness's structured
   question prompt over free text. Offer this shape as a default, not a
   lecture: opus for judgment, design, and gates; sonnet for scoped execution;
   haiku for mechanical decomposition.

3. **Validate.** Reject any value outside the allowed set. A map pointing at a
   model the user cannot run breaks every delegation that reads it.

4. **Write.** Overwrite the whole file so re-runs stay idempotent. Keep its
   shape: the `setup-models rewrites this file` note, the allowed-values line
   with its permission caveat, one table row per role, the inherit rule, the
   fable hard rule. Report the path written and that it governs spawns from
   now on.
