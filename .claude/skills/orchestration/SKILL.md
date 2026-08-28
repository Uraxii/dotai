---
name: orchestration
description: Load when work is big enough to hand off, when phases must run in a set order, or when several subagents run at once. Carries the two-agent roster, the situation-to-skill routing table, the spawn contract every brief fills, the playbook index, the serial pre-ship gate rule, the verdict ledger, and the drain and liveness rules for children.
---

# Orchestration

## Roster

Two roles. Nothing else is a role.

| Role | What it is |
|---|---|
| main thread | Triage, sequencing, cross-workstream synthesis. Only role that may ask the user. |
| `subagent` | Generic delegate. No specialism of own. Brief says what, skill says how. |

A harness may ship its own agent types (read-only explorer, planner). Use
them only where a brief-scoped `subagent` cannot do the job. The `impeccable`
skill spawns its own fleet; invoke the skill, never its agents direct.

External dependency: `ponytail` is a plugin (`ponytail:ponytail`), not a
skill in this tree. Harness without it -> `code-quality` plus
`principle-laziness-protocol` stand in wherever a step names `ponytail`.

## Routing: situation -> skill subagent loads

Role skills:

| Situation | Skill |
|---|---|
| Vague task needs user stories, acceptance criteria, edge cases | `requirements-clarifier` |
| Scope feels paralyzing, or high-stakes op where step order matters | `big-pickle-simple-tasks` |
| Structure, pattern choice, ADRs, skeleton (types, contracts, stubs) | `architect-designer` |
| Scoped, well-defined implementation | `implementation-specialist` |
| Write tests, run suite, diagnose failures, verify fix | `test-automation-engineer` |
| Pre-ship challenge check, before any PR opened or integrated | `skeptic-gate` |
| Own one software workstream end to end, delegate onward | `tech-lead` |
| Own one image generation or editing workstream | `art-director` |

Craft and behaviour skills:

| Situation | Skill |
|---|---|
| Any code written, changed, reviewed | `code-quality` |
| Any step that WRITES code. Mandatory, no exception | `ponytail` |
| About to call something done, or checking delegate's claim | `principle-prove-it-works` |
| Step about to dump bulk (logs, many files, images, big JSON) | `principle-guard-the-context-window` |
| Ponytail ran, diff STILL grows layers, or fix is mass deletion | `principle-laziness-protocol` |
| Tempted to stop and ask permission on reversible work | `principle-never-block-on-the-human` |
| Writing same instruction twice, or same bug class returning | `principle-encode-lessons-in-structure` |
| Picking core types, data shapes, what to build first | `principle-foundational-thinking` |
| Planned rewrite or migration with phases, tempted to add shims | `principle-outcome-oriented-execution` |
| Cutting a feature list, picking a default, or reaching for a config knob | `principle-experience-first` |
| Decision with no precedent, needs competing prototypes | `principle-exhaust-the-design-space` |
| New requirement landing on design that already exists | `principle-redesign-from-first-principles` |
| Non-trivial edits, migrations, analyses, checks: build the rerunnable tool | `principle-build-the-lever` |
| Any prose surface, including your own reply | `unslop` |
| Writing or reviewing docs, RFCs, readmes, PR descriptions, commit messages | `technical-writing` |
| Register for every agent's output and reasoning | `caveman` |
| Hard bug, broken thing, perf regression | `diagnose` |
| Behaviour is testable, want red-green-refactor | `tdd` |
| Session must be picked up by another agent | `handoff` |
| Subagent bloated, tokens high, needs fresh successor | `rotate-agent` |
| Reading legwork against primary sources, delivered as file | `research` |
| Review a diff: several models try to break it, lead judges | `interrogate` |
| What could this change break elsewhere, before it ships | `blast-radius` |
| Design a deep module, place a seam, make code navigable | `codebase-design` |
| Throwaway sketch to settle a design question | `prototype` |
| Creating or editing a SKILL.md | `write-a-skill` |
| Durable notes, sources, boards, artifacts for human review | `agent-workbench` |
| Citing or relying on a web page | `capture-source` |
| Stage, commit, push, open PR | `yeet` |
| Log the decision trail of a run, audit it at end | `show-me-your-work` |
| Recover why something was built this way, nothing recorded | `why` |

## Skill vs playbook

- Capability any step might reach for -> SKILL.
- Sequence picked once per task, up front -> PLAYBOOK.
- Anything user types by name -> SKILL, always.

Skill already owns the shape -> route to skill, no playbook.

## Playbooks

Match task, open file, copy steps into todolist VERBATIM before any
task-specific todo and before reasoning about task. Failure mode: read
playbook, then write bespoke plan quietly dropping its steps. Step you skip
stays in list with one-line `skip: <reason>`. Silent skip not allowed.

| Task shape | Playbook |
|---|---|
| Read-only question: how X works, why Y built that way, is Z true | `playbooks/investigation.md` |
| Reported defect to reproduce, root-cause, fix | `playbooks/bug-fix.md` |
| New or changed behaviour | `playbooks/feature.md` |
| Behaviour-preserving structural change | `playbooks/refactoring.md` |
| Program outliving one agent: many units, phases, standing coordinator | `playbooks/orchestrate.md` |

`playbooks/autonomous-run.md` is a MODIFIER. Layers onto any of the five when
no human awake. Never picked alone.

No playbook fits -> say so, write steps you will follow, hold to them same way.

## Spawn contract

Every spawn carries all of these. Field you cannot fill = task not scoped:
scope it or do not spawn.

```text
GOAL         one sentence outcome, executable by stranger with no chat access
SCOPE        paths this task may write; paths it may not; its branch
SKILLS       skills to load first, by name
CONTEXT      file paths and issue ids; upstream reports pasted in full when
             this task depends on them (subagents cannot see siblings)
ACCEPTANCE   checkable criteria, one per line
VERIFY       exact commands to run, plus known gotchas
TIMEBOX      rough runtime cap; on expiry return partial findings and stop
FORBIDDEN    out-of-scope edits, task-specific bans, read-only or no-pixels
REPORT       status, branch, head SHA, verdict, what was actually run,
             deviations, suggested follow-ups
```

Size to task. One-command task collapses to paragraph still naming goal,
scope, verify command, report shape.

- Model pinned PER CALL via the spawn call's `model` argument. Never in frontmatter.
  Map: `models.md`.
- Constraints go in brief text, not tool config. Read-only means FORBIDDEN
  says "no writes, no commits, inspection commands only". No-pixels means
  FORBIDDEN says "never load image pixels, hold paths and verdict text only".
- Standing orders: paste the user's global instructions file (`CLAUDE.md`, `AGENTS.md`, or harness equivalent) into every spawn. Directives
  decay; each dropped one costs user turn.
- Never resume-chain a brief. Scope change -> fresh spawn with consolidated
  scope. Bloated agent -> `rotate-agent`.

## Verdict ledger

Verdict pinned to commit SHA, never to memory or transcript. Record every gate
verdict AND its resolution as bd note on tracking issue via `agent-workbench`:
`verdict=<X> sha=<head> by=skeptic-gate ran=<cmd> resolution=<fix|accepted|open>`.

- New head SHA voids verdict. Re-gate after any commit, rebase, amend.
- CI green is input to verdict, not verdict.
- BLOCK gets fix task, not re-gate of same SHA.
- Before shipping: every change on branch has PASS for current SHA.
- When a `show-me-your-work` trail is active, the gate verdict also goes in as a row on that trail, not just the bd note.

## Before shipping

Gate required before any PR opened or integrated. Spawn `subagent` loading
`skeptic-gate`. Any ONE trigger is enough:

- Architecture change.
- Security or trust-boundary change.
- Netcode, shared state, or replication change.
- Migration.
- Public API or schema change.
- Large cross-cutting change.
- Verification weak or missing.
- Tests passed but result looks suspicious.

Serial rule: spawn ONE gate. Wait for verdict. Fix. Spawn ONE FRESH gate.
Never batch, never parallel. Gate calls are dependency chain, not independent
tool calls. Non-PASS verdict halts delivery until resolved.

## Drain and liveness

- Never resume child just to check on it. Resume restarts an idle agent.
  Probe read-only instead.
- Account for every child spawned. Completion is queue event, not interrupt;
  note it, keep working, drain queue before declaring done. Unaccounted child
  is unfinished work.
- Retry by failure mode, never blindly. Cap-hit or OOM -> respawn smaller
  scope. Network -> retry as is. Tool error -> different model. Unknown ->
  once.
- Bound own retries: two, then mark unit blocked and replan around it.
  Cannot replan -> bubble up BLOCKED naming exactly what stuck.

## Hard rule

NEVER spawn `fable`, `sol`, or `luna` agents without explicit user permission.
No exceptions, no inference from silence.
