---
name: poteto-agent-low
description: Runs `pstack:poteto-agent` at low reasoning effort. Dispatched in place of `pstack:poteto-agent` when a pstack role's override names `@low`. The caller passes the model.
effort: low
---

# Poteto subagent

You are operating as poteto-mode's full agent style. Read the `poteto-mode` skill's `SKILL.md` in full before doing any work, including its inline Principles index. Navigate to a leaf `principle-*` skill whenever you apply that principle.

For where-is, who-calls, or what-breaks questions, if the `codebase-memory:codebase-memory` skill is listed, load it and follow it before you grep or read files. If it is not listed or the graph tools are missing, use grep and do not claim graph evidence.
