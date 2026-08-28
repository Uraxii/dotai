---
name: rotate-agent
description: Rotate a bloated long-running subagent (orchestrator, specialist, any persistent delegate) into a fresh one via a gitignored transient handoff doc. Use when a delegate's token usage passes ~250k, when the user says "rotate the agent" / "context is bloated" / "start a fresh agent", or before handing a long pipeline to a successor agent. Applies to ALL subagents; orchestrators apply it to their own specialists.
---

# Rotate agent

Swap a bloated subagent for a fresh one with zero pipeline loss. The SPAWNER
runs this, never the bloated agent: it cannot self-certify rotation.

Rotate when the delegate passes ~250k tokens, when its replies degrade (forgets
policies, repeats work), or when the user asks.

1. **Wrap up.** Message the agent: finish IN-FLIGHT work only, no new phases.
   Then write a handoff per the `handoff` skill to
   `docs/handoffs/<agent-role>.md`, adding exact pipeline position (each task,
   its stage, briefs issued) and key seams. Report that path back. Stop.
2. **Verify.** Never trust the wrap-up report. File exists at the reported
   path, tree otherwise clean, sections match repo reality (spot-check commits
   and test claims).
3. **Spawn the successor.** Same type, fresh. Founding brief carries the
   handoff path plus any user directive VERBATIM; the successor inherits brief
   and handoff only, never chat history.
4. **Confirm pickup.** Successor's first report restates the pipeline from the
   handoff. Mismatch -> fix the handoff, not the successor's memory.

`docs/handoffs/` is gitignored and transient. Add the ignore entry if missing.
Never commit it; the next rotation overwrites the file.

Agent dead or unresponsive -> write the handoff yourself from repo evidence
(git log, docs, test runs), then step 3.
