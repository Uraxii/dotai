---
name: skill-quality
description: >-
  Reviews or authors SKILL.md files for actionable skill smells and focused
  repairs.
---

# Skill smells

Use when authoring, changing, or reviewing `SKILL.md`. Find smell. Make
smallest repair. Smell = heuristic, never excuse to add needless ceremony.

## Under-specified guidance

- **Stepless workflow.** Multi-step workflow = prose block. Split where order
  changes work.
- **Option buffet.** Many tools, no default. Pick default. Name alternative's
  trigger.
- **Missing utility script.** Repeated deterministic work belongs in script.
  Add only when repeat or verification earns it.
- **Missing decision tree.** Material branch, no chooser. Add short rule there.

## Over-prescribed guidance

- **Series of commands.** Fixed commands, paths, or args block adaptation.
  State goal + invariant. Exact commands stay for fragile or safety work.

## Missing verification and feedback

- **No validation step.** One-shot artifact. Add check on real result.
- **Execute without a plan.** Complex, costly-to-reverse task skips plan or
  mid-course validation. Add one.
- **Never asks human.** Workflow needs taste, authority, or missing context;
  no ask route. Not for autonomous work with complete inputs + authority.

## Missing follow-through guards

- **Rationalization loophole.** Required work skipped as unnecessary. State
  observable completion condition.
- **No progress tracking.** Long workflow loses its place. Add minimal state
  only when that risk exists.

## Context bloat

- **Undelegated detail.** Conditional, low-level detail in entrypoint. Move to
  reference or script. Keep always-needed instructions inline.
- **Lengthy skill body.** Body >5,000 words. Cut, split, or route detail out.
- **Lengthy skill name.** Name >64 chars. Rename for discovery.
- **Lengthy skill description.** Description >1,024 chars. Keep capability +
  routing only.
- **Confusing skill description.** Missing what, when, or discovery keywords.
  Add missing part.

## Missing safeguards

- **No guardrails.** No constraint against real bad/impossible work. Add only
  for real failure mode.
- **Buried gotchas.** Critical warning easy to miss. Put beside constrained
  decision under clear heading.
- **Missing usage rules.** No trigger, scope, or permission rule. Add minimum.
- **Missing caveats.** Common failure case has no resolution. Add only when
  likely and action-changing.

## Inadequate contextual grounding

- **Missing example.** Example would clarify input/output; none exists. Add
  smallest representative example, not tutorial two.
- **Time-sensitive skill.** File embeds decaying fact. Query source at use,
  name update rule, or cut claim.

## Security hazard

- **XML in description.** Description has XML tags. They can inject
  instructions. Use plain text.

## Convention and style violations

- **Backslash path.** Skill-dir path uses `\\`. Use `/`.
- **Unclear skill name.** Name hides capability or action. Rename for cold
  reader.
- **Non-third-person description.** Description not third person. Rewrite as
  capability statement.

## Unstructured output

- **Missing template.** Specific output format, no template. Add minimum
  format or canonical source.
