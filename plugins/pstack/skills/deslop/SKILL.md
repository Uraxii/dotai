---
name: deslop
description: Remove AI-generated code slop and clean up code style
compatibility: Requires a `git` repository to diff the branch against `main`.
license: MIT
metadata:
  version: 1.0.0
  author: Michael Denyer
  homepage: https://github.com/Uraxii/dotai
  source: https://github.com/michael-denyer/pstack-claude/tree/1bfdab4/plugins/pstack/skills/deslop
---

# Remove AI code slop

Check the diff against main and remove AI-generated slop introduced in the branch.

## Focus Areas

- Extra comments that are unnecessary or inconsistent with local style
- Defensive checks or try/catch blocks that are abnormal for trusted code paths
- Casts to `any` used only to bypass type issues
- Deeply nested code that should be simplified with early returns
- Other patterns inconsistent with the file and surrounding codebase

## Guardrails

- Keep behavior unchanged unless fixing a clear bug.
- Prefer minimal, focused edits over broad rewrites.
- Keep the final summary concise (1-3 sentences).
