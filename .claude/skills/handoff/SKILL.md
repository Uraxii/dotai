---
name: handoff
description: Compact the current conversation into a handoff document for another agent to pick up. Use when the user asks for a handoff, session compact, continuity note, or wants another session/agent to continue current work.
argument-hint: "What will the next session be used for?"
---

# Handoff

## Overview

Create a handoff document that lets a fresh agent continue the current work without replaying the full conversation. Prioritize recall over brevity: capture everything a fresh agent needs, then trim. Reference durable artifacts (PRDs, plans, ADRs, issues, commits, diffs, project docs) by path instead of duplicating them, but only after verifying the referenced document actually contains the claim. When in doubt, include the detail inline.

In long sessions, do not wait until the end: append decisions, constraints, and verbatim user directives to the handoff file (or a working notes file) at the moment they are established. A handoff reconstructed from an already-degraded context is the main cause of lost details.

Save the handoff document to the temporary directory of the user's operating system, not the current workspace. On Linux/macOS, prefer `/tmp`. On Windows, use the path from `%TEMP%`/`$env:TEMP`.

## Which mode

A referenced handoff file (e.g. `@/tmp/handoff_dotfiles_agent-orchestration_3_1784659200.md`) means CONSUME, not create. It is an instruction source: read it, load the suggested skills, inspect the named workspace and artifacts, execute the immediate next steps. Do not write another handoff unless explicitly asked.

Asked to EXPLAIN how handoffs or briefs work: do not execute the handoff's next steps. Read the file, then explain the consumption model. Handoff is temporary context, not source-of-truth; the next agent loads suggested skills, verifies named artifacts, preserves constraints and risks, and acts only when the user asks for continuation.

Never rewrite existing project documents while creating a handoff. Reference them by path or URL.

## Inputs

If the user passes arguments, treat them as the focus for the next session and tailor the handoff around that future work.

Example arguments:
- `implement milestone 0`
- `continue debugging camera scaling`
- `prepare PR review`

If no arguments are supplied, infer the likely next-step focus from the current conversation and label it as inferred.

## Procedure: consuming a handoff

Use this flow when the user references an existing handoff file and appears to want continuation rather than a new handoff.

1. Read the handoff file first.
   - Treat a referenced handoff file in the OS temp directory, or a pasted handoff path, as the current session brief.
   - Do not ask what to do next if the handoff contains explicit `Immediate Next Steps`.

2. Load suggested skills before acting.
   - Invoke skills listed under `Suggested Skills` when they are relevant to the immediate next step.
   - If a suggested skill governs later work but not the current step, note it mentally and defer loading until needed.

3. Inspect the named workspace and durable artifacts.
   - Verify branch/status before editing or committing.
   - Read the raw files or docs named as sources of truth instead of relying only on the handoff summary.

4. Execute the immediate next steps.
   - Preserve raw handoff-referenced artifacts unless the handoff says otherwise.
   - Update durable project docs with distilled decisions, not duplicated transcripts.
   - Commit/push only when the handoff or user request makes that the expected continuation and the diff is verified.

5. Verify completion.
   - Check git status/log after commit/push when working in a repository.
   - Search for stale/conflicting language when the task was to update decisions or requirements.

6. Propagate the chain forward (when handing off to the next link).
   - If the workstream continues (more tickets/tasks remain), the handoff you write for the next session must carry the prior `Carry-Forward Context` forward: keep the overarching goal, cross-cutting decisions, standing conventions, and chain-wide directives; update the task-sequence status and swap the task-specific sections for the new task.
   - The carry-forward context is living, not frozen. If work on this task changed a prior decision, revise that entry (and note what it superseded and why); if it produced a new fact, constraint, convention, or directive that later tasks need, ADD it. The next handoff should reflect the chain's current truth, not the state at chain start.
   - Losing or staling carry-forward context is the main failure of chained handoffs. Treat that section as cumulative and maintained, never as "already handled."

## Procedure: creating a handoff

1. Identify the active workstream and the wider chain.
   - Summarize the current objective in 1-3 sentences.
   - Include the intended next-session focus from the user arguments, if present.
   - If this handoff is one link in a sequence (e.g. a set of tickets or milestones done in order), capture the WHOLE workstream, not just the next task: the overarching goal, the full task list with done / current / remaining status, and every decision, convention, or constraint agreed up front that binds all the tasks. This is carry-forward context and it must survive the entire chain. Do not prune it just because early tasks are finished. A decision made before task 1 is exactly what a task-3 successor most often loses. When this handoff continues a prior one, carry its Carry-Forward Context forward and keep it current: revise entries that later work changed (noting what was superseded and why), add new facts/constraints/conventions/directives that downstream tasks will need, and never silently drop an entry that still binds remaining tasks.

2. Gather transient context, recall first.
   - Include decisions with their rationale, constraints, unresolved questions, and immediate next steps.
   - Capture user directives verbatim: corrections, vetoes, terminology preferences, scope limits, and every "don't do X" instruction. Quote them exactly; do not paraphrase. Paraphrase loses the nuance the user will otherwise have to re-teach.
   - Record failed approaches and dead ends, with why they failed, so the next agent does not retry them.
   - Anchor state claims to ground truth (git status/log, test output, files on disk), not to memory of the conversation.
   - Do not duplicate full PRDs, plans, ADRs, issue bodies, diffs, commits, or generated artifacts. Reference them by path, URL, branch, or commit, but verify the referenced document actually contains the claim before relying on the reference. When in doubt, include the detail inline.

3. Redact sensitive data.
   - Remove API keys, tokens, passwords, cookies, private credentials, SSH keys, and raw auth headers.
   - Avoid unnecessary personally identifiable information.
   - If a secret is relevant, write `[REDACTED_SECRET]` and explain what kind of credential is needed.

4. Include a Suggested Skills section.
   - List skills the next agent should invoke before acting.
   - Include why each skill is relevant.
   - Prefer exact skill names.

5. Completeness pass (mandatory, before writing the final version).
   - Re-scan the entire conversation specifically for: user corrections and steering, explicit vetoes and prohibitions, terminology and naming preferences, scope limits, and approaches that were tried and abandoned.
   - Negative constraints ("don't", "never", "stop doing X") are the details most often lost in summaries. Hunt for them explicitly.
   - Anything found that is missing from the draft goes into `Verbatim User Directives` or `Failed Approaches / Do NOT`.

6. Write the handoff to the OS temp directory.
   - Filename: `handoff_<project>_<topic>_<chain number>_<unix time>.md` (example: `handoff_dotfiles_agent-orchestration_3_1784659200.md`). Field separators are underscores; the topic slug may keep internal hyphens. Unix time is seconds at write time. The destination directory convention is unchanged.
   - `<project>` is the actual repo/project the work targets (e.g. `gvn` for work on `~/Projects/gvn`), never the session cwd or a parent dir like `Projects`. User's rule verbatim: "When I say project I mean the project being worked on. Not the base directory the session is running from. Ex. bad: Claude session in Projects, Project = Projects. good: working on ~/Projects/gvn, Project = gvn."
   - Chain number is the position in the chain, starting at 1. A successor handoff continuing the same effort increments it: find the predecessor (the highest chain number among `handoff_<project>_<topic>_*` files in the temp directory) and add 1.
   - RECOMMEND starting a new chain (reset to 1 with a fresh topic slug) when: the effort or destination changes rather than continues; the topic has drifted so far the old slug misleads; the prior chain concluded (its work shipped or merged) and the new work is a fresh effort; or the chain has grown long enough that carrying its full lineage adds noise rather than context. You recommend; the human decides.
   - Do not write it into the repo or current workspace unless the user explicitly asks.

7. Report the created file path to the user.
   - State the full absolute path to the handoff document (e.g. `/tmp/handoff_dotfiles_agent-orchestration_3_1784659200.md`), not a relative path, a `~`-path, or just the filename, so the user can copy it straight into a new session.
   - Put that path on its own line so it is easy to select.
   - Keep the rest of the final response short. Mention any assumptions or redactions.

## Recommended document structure

```markdown
# Handoff: <short title>

Generated: <ISO-like local timestamp>
Next-session focus: <user argument or inferred focus>

## Active Workstream
<1-3 sentence summary.>

## Carry-Forward Context (propagate through the whole chain, do NOT prune)
<Only when this is one link in a sequence of tasks/tickets/milestones. Carry this
section forward into every subsequent handoff and keep it current: it is
cumulative and living, not task-specific and not frozen. Revise entries that
later work changed (note what was superseded), and add new chain-wide facts as
they emerge.>
- Overarching goal: <the end state the whole chain is working toward>
- Task/ticket sequence + status: <e.g. T1 done, T2 in progress, T3-T5 pending>
- Cross-cutting decisions (bind all tasks): <decision, because rationale>
- Standing conventions / patterns: <naming, structure, style agreed once, applies throughout>
- Directives that apply chain-wide: "<verbatim user instruction that governs every task>"
- Global do-NOT (whole chain): <approach rejected for all tasks, and why>

## Current State
- Repo/workspace: <path or URL if relevant>
- Branch/commit/status: <only if needed>
- Durable artifacts to read first:
  - <path or URL>

## Verbatim User Directives
- "<exact quote of user instruction, correction, veto, or preference>"

## Key Decisions + Rationale
- <decision>, because <why it was decided this way>

## Failed Approaches / Do NOT
- <approach tried and abandoned, and why it failed>
- <explicit prohibition from the user>

## Immediate Next Steps
1. <next action>
2. <next action>

## Open Questions / Risks
- <question or risk>

## Suggested Skills
- `<skill-name>`: <why>

## Sensitive Info Handling
- No secrets included.
- <or describe redactions>
```
