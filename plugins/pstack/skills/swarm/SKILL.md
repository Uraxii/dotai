---
name: swarm
description: "Fan out N parallel workers, drain them, and return one report. Use for /swarm, 'swarm this', or parallel coverage, races, gauntlets, and exploration."
disable-model-invocation: true
---

# Swarm

Fan out N parallel isolated workers. They may cover separate slices, race the same brief, or mix both. The parent waits, aggregates, and returns one report.

## Start

Before launching anything, create one step bead for each phase, per the Phases of a skill section of [Run records](../ticket-work/references/run-records.md#phases-of-a-skill).

1. Frame
2. Fan out
3. Aggregate
4. Report

## Phase A: Frame

1. State the done predicate and the artifact or report the swarm must return.
2. Choose the shape. Partition into slices, race N workers on identical briefs, or mix both. For a race or mixed shape, declare `first pass`, `rank all`, or `best-of` before spawning.
3. Set N from the user or derive it from the shape. N is total workers, not the runner concurrency limit.
4. Pick the worker model from the `swarm workers` role in `models.json`, two directories up from this skill's directory. Use the first name in your harness's list. The [Models section of `poteto-mode`](../poteto-mode/SKILL.md#models) tells how to find the file, how the override sheet changes a role, and what to do when the harness rejects a name. For `auto` or `inherit-parent`, omit `model` so the workers run on the parent model. For a model race, name each arm's model up front.
5. Give each worker its own writable output when it writes. When workers verify or measure commits, each brief names the exact SHAs. A measurement brief also names the method (sample count, what one sample is, order). The worker records both in its result.

## Phase B: Fan out

Spawn all N workers through the supported agent API. Use the step 4 model, or the parent-model default for `auto` or `inherit-parent`. Grant each worker its required access. Use background execution when supported. A remote runner is optional and must reach the named inputs.

Give each worker the exact branch and SHA. Check that its checkout has that SHA before work starts.

Every brief stands alone. Include the goal, scope, exact slice or race arm, how to verify, and what to report. When the worker works in a checkout, the brief tells it to run the **index-the-codebase** skill first. Reports use `PASS`, `ISSUES`, or `BLOCKED` with evidence. A worker that can prove a defect reports `ISSUES` and lists every issue it can prove, not only the first.

If a worker drops out, proceed with N-1 and note it.

## Phase C: Aggregate

Read the terminal results. Drop a result that does not record the SHAs and method its brief names, and respawn that worker once. After a second miss, record a gap. A gap does not count as a pass. For coverage, every required slice needs a result. For a race, apply the selection rule declared up front. Use first pass, rank all, or best-of. Do not paste raw worker dumps.

Keep a compact result table, one-line evidenced issues, and explicit gaps or dropouts.

## Phase D: Report

Return one consolidated in-chat report with the table, issue one-liners, gaps or dropouts, and the race rule when used.

Use [Platform adaptation](../poteto-mode/references/platform-adaptation.md) for tool APIs, skill locations, and evidence limits.
