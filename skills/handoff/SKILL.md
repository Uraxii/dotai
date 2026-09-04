---
name: handoff
description: Compact the current conversation into a handoff document for another agent to pick up. Use when the user asks for a handoff, session compact, continuity note, or wants another session/agent to continue current work.
---

# Handoff

A handoff lets a fresh agent continue the work without replaying the conversation. Recall beats brevity: capture everything the successor needs, then trim.

Write it to `.handoffs/` at the project root, gitignored (add the entry if missing). Never commit it. Never rewrite project documents while creating one.

In a long session, append decisions, constraints, and verbatim user directives to the handoff file as they are established. A handoff reconstructed from an already-degraded context is the main cause of lost detail.

A hook can flag context pressure before the agent notices it. Optional, not installed, setup in `references/hook-setup.md`.

## Which mode

A referenced handoff file means CONSUME, not create. Read it, load its suggested skills, inspect the named artifacts. The invocation argument is the work order; the handoff is context for it. An argument naming one task (an answer, a fact, one step) authorizes that task only: do it, then report the remaining next steps as status, not as a backlog to start. No argument means the full `Immediate Next Steps` list is the work order. Do not write another handoff unless asked.

Asked to EXPLAIN handoffs: read the file, explain the consumption model, execute nothing.

When creating, the invocation argument names the next session's focus to record in the handoff. Absent, infer the focus from the conversation and label it inferred.

## Consuming

1. Read the handoff file first and treat it as the session brief. Do not ask what to do next when it names `Immediate Next Steps`.
2. Invoke the `Suggested Skills` relevant to the current step; defer the rest until needed.
3. Verify branch and status before editing. Read the artifacts named as sources of truth rather than trusting the summary.
4. Execute the next steps inside the work order, in listed order. Update durable project docs with distilled decisions, not transcripts. Commit or push only when the handoff or the user makes that the expected continuation and you verified the diff.
5. Verify completion: check `git status`/`log` after a commit, and search for stale or conflicting wording when the task was to update decisions.

## Creating

1. **Frame the workstream.** Summarize the objective in 1-3 sentences plus the next-session focus.
2. **Carry the chain.** When this handoff is one link in a sequence, capture the whole workstream: overarching goal, full task list with done / current / remaining status, and every decision, convention, or constraint agreed up front that binds all tasks. That is carry-forward context and it must survive the entire chain. It is cumulative and living: revise entries later work changed (noting what was superseded and why), add new chain-wide facts, and never drop one that still binds remaining tasks. Losing it is the main failure of chained handoffs.
3. **Gather transient context, recall first.** Decisions with rationale, constraints, open questions, immediate next steps. Quote user directives verbatim: corrections, vetoes, terminology, scope limits, every "don't do X". Paraphrase loses the nuance the user has to re-teach. Record failed approaches and why they failed. Anchor state claims to ground truth (`git status`, test output, files on disk), not to memory.
4. **Reference, don't duplicate.** Point at PRDs, plans, ADRs, issues, diffs, and commits by path, URL, branch, or commit, but verify the referenced document actually contains the claim first. In doubt, inline the detail.
5. **Redact.** Strip API keys, tokens, passwords, cookies, SSH keys, raw auth headers, and unnecessary PII. Write `[REDACTED_SECRET]` and name what kind of credential the successor needs.
6. **List suggested skills** with why each is relevant, by exact name.
7. **Completeness pass, mandatory.** Re-scan the whole conversation for user corrections, vetoes, terminology preferences, scope limits, and abandoned approaches. Negative constraints are the detail summaries lose most. Anything found goes into `Verbatim User Directives` or `Failed Approaches / Do NOT`.
8. **Write the file.** Name it `handoff_<project>_<topic>_<chain number>_<unix time>.md`, underscores between fields, hyphens allowed inside the topic slug. `<project>` is the repo the work targets, never the session cwd. User's rule verbatim: "When I say project I mean the project being worked on. Not the base directory the session is running from. Ex. bad: Claude session in Projects, Project = Projects. good: working on ~/Projects/gvn, Project = gvn." Chain number starts at 1; a successor finds the highest existing `.handoffs/handoff_<project>_<topic>_*` and adds 1. Recommend a fresh chain when the effort changes rather than continues, the slug has drifted, the prior chain shipped, or the lineage has grown into noise. You recommend, the human decides. Run `skills/handoff/scripts/new-handoff.sh <project> <topic>` to create the named, skeleton-filled file in one step instead of doing this by hand.
9. **Report the full absolute path** on its own line. Keep the rest of the reply short, naming any assumptions or redactions.

Document structure: `references/document-structure.md`.
