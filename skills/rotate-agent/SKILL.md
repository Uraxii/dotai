---
name: rotate-agent
description: Rotate a bloated long-running subagent (orchestrator, specialist, any persistent delegate) into a fresh one via a gitignored transient handoff doc. Use when a delegate's token usage passes ~250k, when the user says "rotate the agent" / "context is bloated" / "start a fresh agent", or before handing a long pipeline to a successor agent. Applies to ALL subagents; orchestrators apply it to their own specialists.
---

# Rotate agent

Swap bloated subagent → fresh one, zero pipeline loss. Handoff doc =
successor's starting context.

Applies to every long-running subagent. SPAWNER runs procedure: main
session rotates own delegates; orchestrator rotates own specialists.

## When

- Delegate token usage >~250k.
- Replies degrade (forgets policies, repeats work).
- User asks.

Spawner enforces. Bloated agent never self-certifies rotation.

## Handoff file

Doc contents: the `handoff` skill. Rotation overrides its LOCATION only.

Per-agent → no clobber: `docs/handoffs/<agent-role>.md` (e.g.
`docs/handoffs/tech-lead.md`, `docs/handoffs/impl-network-cli.md`), NOT the
OS temp dir `handoff` defaults to. Rotating agent MUST report exact path to
spawner in final message. Spawner never guesses.

TRANSIENT, never in git history: `docs/handoffs/` gitignored (add
entry if missing). Never commit. Successor overwrites at own rotation.

## Workflow

1. **Wrap-up order.** Message the bloated agent:
   - Finish IN-FLIGHT only: spawned specialists complete, results
     integrated, milestone commits landed, tree clean. No new phases.
     Note exact pipeline position.
   - Write handoff at `docs/handoffs/<agent-role>.md`. Contents per the
     `handoff` skill, plus two rotation extras: exact pipeline position
     (each task, its stage, briefs issued) and key seams (entry points,
     invocations, locations). (No-direct-work policy? this one file
     exempt, report artifact, not project work.)
   - NO commit (dir gitignored; add entry if missing).
   - Final report states handoff path. Stop.
2. **Verify.** Never trust wrap-up report:
   - File exists at reported path + untracked. Tree otherwise clean.
   - Read handoff → sections present, match repo (spot-check commits,
     test claims).
3. **Spawn successor.** Same type. Founding brief:
   - Handoff path (read first).
   - User directives VERBATIM for risky/scoped work (agents may refuse
     peer-relayed authority; verbatim wording + repo-verifiable
     evidence in FOUNDING brief passes provenance, no round-trips).
   - Rotation-surviving policies restated (successor inherits brief +
     handoff ONLY, never chat history).
4. **Confirm pickup.** Successor's first report restates pipeline
   from handoff. Mismatch → fix handoff, not successor memory.
5. **Propagate up.** Orchestrator rotating specialist → report
   rotation (old id, new id, handoff path) to own spawner.

## Notes

- AUTONOMOUS: spawner executes all steps on task-notifications without
  user prompting. Handoff reported → successor spawned immediately.
- Keep old agent id until successor confirms pickup (loose-end Q&A).
- Agent dead/unresponsive → write handoff yourself from repo evidence
  (git log, docs, test runs) → step 3.
- Repeat rotations: successor rewrites own handoff file. Doc = current
  baton only.
