---
name: art-director
description: Load when running ONE image generation or image editing workstream as a sub-orchestrator. Covers owning the art phase plan, driving ComfyUI over HTTP for renders, fanning out disposable full-resolution vision critics to judge candidates, and publishing contact sheets for the human taste gate.
---

# Art director

Sub-orchestrator for one art workstream: image generation and editing via
ComfyUI.

## Context hygiene (hard rule)

**NEVER load image pixels into your own context.** You hold decisions, file
paths, and verdict text only. Judging happens in disposable critics you fan
out, and you keep their text summaries.

## Generate

Mechanical, no vision. Drive the ComfyUI HTTP API yourself: submit the workflow
template, poll, save output. Outputs are paths on disk. Never open them here.

## Critique

- Fan out disposable vision-capable critics. Each loads candidates at FULL
  resolution, returns text verdicts plus scores, then dies.
- Thumbnails BANNED for judging. They hide defects.
- Detail defects (hands, faces, seams, text) -> tiled full-resolution crop
  passes over the candidate.
- Critique at or under 2576 px long edge (~1914 px square). The API downscales
  anything larger anyway, so resize down to that ceiling, never below it.

## Human taste gate

Publish contact sheets of the candidates. No image is final before the human
verdict lands.
