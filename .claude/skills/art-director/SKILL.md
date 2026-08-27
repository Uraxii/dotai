---
name: art-director
description: Load when running ONE image generation or image editing workstream as a sub-orchestrator. Covers owning the art phase plan, driving ComfyUI over HTTP for renders, fanning out disposable full-resolution vision critics to judge candidates, and publishing contact sheets for the human taste gate.
---

# Art director

Sub-orchestrator, one art workstream (image gen + edit via ComfyUI).

FIRST ACTION: load the `orchestration` skill.

## Context hygiene (hard rule)

- **NEVER load image pixels into your own context.** Hold decisions, file
  paths, verdict text only. Judging happens in disposable critics you fan out,
  and you keep only their text summaries.
- Any agent holding images rotates early (`rotate-agent` skill). Watch
  subagent_tokens.
- Model not pinned here. Orchestrator pins it through the Agent tool's `model`
  argument. Map lives in the `orchestration` skill, file `models.md`.

## Generation (drive ComfyUI yourself)

Mechanical, no vision. Use the `comfyui` skill to submit any workflow
template, poll, and save output. Outputs are paths on disk. Never open them
here.

## Critique (fan-out disposable full-resolution critics)

- Fan out disposable critic agents (vision-capable): load candidate images at
  FULL RESOLUTION, return text verdicts plus scores, then die.
- Thumbnails BANNED for judging. Hide defects.
- Detail defects (hands, faces, seams, text): run tiled full-resolution crop
  passes over candidate.
- Critique images at or under 2576 px long edge (~1914 px square). API server
  downscales anything larger anyway, so resize down to that ceiling, never
  below it.
- Advisor as critic: only if verdict visible, meaning Opus 4.8 (Fable-5
  advisor blocked in Claude Code, returns encrypted results).
  Images-to-advisor UNVERIFIED; until probed, use plain fan-out vision
  critics, which work natively.

## Human taste gate

- Publish contact sheets of candidate renders, wait for human verdict before
  any image treated as final.
