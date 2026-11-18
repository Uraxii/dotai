---
description: 'Show OX Security - VibeSec status: is OX active, and which guidelines are on this session'
allowed-tools: Bash("${CLAUDE_PLUGIN_ROOT}/hooks/ox" --status)
---

Use the Bash tool to run this command:

"${CLAUDE_PLUGIN_ROOT}/hooks/ox" --status

Then output its stdout verbatim inside a fenced code block. No text before or after it, no summary, no commentary, no reformatting. If the command prints nothing, say that OX status is unavailable.
