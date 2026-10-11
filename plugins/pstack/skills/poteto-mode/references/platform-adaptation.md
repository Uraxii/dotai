# Platform adaptation

Shared skills describe the task. The active tool supplies the execution API.
Check the installed tool's help and available tools before each first use.
Do not pass a parameter that the active API does not support.

## Skill authoring and locations

Use your harness's skill-authoring guidance.
Claude Code maps this to `plugin-dev:skill-development` when installed.
For Codex and Copilot CLI, discover the available authoring guidance.
Do not assume a built-in authoring skill exists.

| Tool | Project skill directory | Personal skill directory |
|---|---|---|
| Claude Code | `.claude/skills/` | `~/.claude/skills/` |
| Codex | `.agents/skills/` | Resolve from the active configuration. |
| Copilot CLI | `.github/skills/` or `.agents/skills/` | `~/.copilot/skills/` or `~/.agents/skills/` |

Preserve an existing skill's location and category.
For a new skill, resolve one supported directory before you write.
Verify discovery in a fresh session. Do not write to every tool's directory.

## Agents and questions

Use the active tool's agent API for spawn, wait, status, resume, and stop.
Claude Code supplies the Agent tool and plugin agent definitions.
Copilot CLI supports plugin agents in `agents/*.agent.md`.
Use the agent's existing ID and duties. Select background execution only
when the exposed API supports it. Give each writer its own checkout.

Shared agent files keep their existing IDs and duties.
Resolve the ID through the active tool before you spawn.

| Definition | Claude Code ID | Copilot CLI ID |
|---|---|---|
| `poteto-agent.agent.md` | `pstack:poteto-agent` | `pstack:poteto-agent` |
| `comment-sicko.agent.md` | `pstack:Comment Sicko` | `pstack:comment-sicko` |
| `zakia.agent.md` | `pstack:zakia` | `pstack:zakia` |

Claude Code uses the frontmatter name. Copilot CLI uses the file ID.
Do not change the persona name to make the two naming rules look identical.

Codex uses its exposed agent API with a complete skill brief.
Do not assume Codex discovers Claude-format agent definitions.
When a named agent cannot load, pass its existing instructions to a supported
worker. If no worker API exists, report the missing capability.
An independent review requires a fresh agent. Do not replace it with self-review.

Use the role lists in `models.json` and the active tool's override sheet.
Keep the existing fallback when a model is unavailable.
For `auto` or `inherit-parent`, use the API's parent-model default.

Use the active tool's structured question API when available.
Otherwise ask one concise question in chat.
Grant the required file and connector access through supported permissions.
A read-only task forbids writes. It does not define connector availability.
Verify the actual tool set before you report a missing connector.

## Wake and recovery

Use an exposed event watcher or scheduler when available.
Otherwise run a bounded loop in the active session with an explicit finish
condition and a stop condition. Report that it ends when the session ends.
Do not promise background continuation without a verified runner.

Use supported worker status, beads, branch state, and PR evidence for recovery.
A transcript file does not prove that a worker is live.
After a restart, check each worker's status before you reconnect or replace it.
A remote runner is optional. Use it only when its access and status API work.
For a worker without database access, include the required context in its brief
and record its returned report on the bead.

## Transcript evidence

Resolve an explicit active-project transcript source, exported conversation,
or supplied digest. Do not search an implicit home directory or another project.
Use the source's actual format. Do not assume JSONL keys or directory layouts.
Check the opening prompt or session ID before you select a conversation.
If no source resolves, record missing transcript evidence and use a supplied
digest. A digest cannot prove unrecorded tool calls or full chain-following.

Pass the resolved source and its project scope to every transcript reader.
For worktree audit, pass the transcript directory as the second argument.
Without evidence, chat recency is unknown and cannot authorize cleanup.

## App verification

Select the project's verification skill or an available driver by interface.
Use a browser driver for browser apps, a terminal driver for CLIs, and the
project's simulator driver for mobile apps.
Report a missing driver. Do not require an unrelated plugin.

## Plugin formats and load limits

Claude Code uses `.claude-plugin/plugin.json` and `hooks/claude-hooks.json`.
Codex has `.codex-plugin/plugin.json` with skill and hook paths.
The root `plugin.json` is legacy metadata without an Agent Plugins schema.
Copilot CLI uses that root metadata and `hooks.json` with camelCase events.
Do not add a schema without checking the resulting component discovery.

The reminder emits plain text for Claude Code, `hookSpecificOutput` for Codex,
and `additionalContext` for Copilot CLI.
A subprocess check proves the output contract. It does not prove session delivery.

Use a temporary profile and a copy of the candidate for each load check.
Record the version, selected manifest, skills, agent IDs, and session-hook result.
Record authentication and runner limits. An installation count is not a support pass.
