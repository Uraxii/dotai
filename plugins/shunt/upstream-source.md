# shunt plugin source

Vendored from Spotify's `portal-ai-plugins` marketplace.

- Source: https://github.com/spotify/portal-ai-plugins/tree/e14bdb1dc894e0a2ef150fa811db5308ae2ddb37/plugins/shunt
- Revision: `e14bdb1dc894e0a2ef150fa811db5308ae2ddb37` (shunt's last touch on that repo; repo main is `3c24ca3`)
- License: Apache-2.0, retained in [LICENSE.md](LICENSE.md).
- Upstream issue: https://github.com/spotify/portal-ai-plugins/issues/10

## Patched fork

`hooks/check-file-size` and `hooks/check-bash-read` printed a legacy
top-level `{"decision": "allow"}` on every pass-through and
`{"decision": "block", "reason": ...}` on a block. Current Claude Code
rejects a top-level `"allow"` (the legacy `decision` field only accepts
`approve`/`block`), so nearly every `Bash` call errored (upstream issue #10).

Both hooks now follow the current `PreToolUse` hook output schema:

- Pass-through: no stdout, `exit 0`. This defers to Claude Code's normal
  permission flow, the same as before the hooks existed for that call.
  Emitting `permissionDecision: "allow"` instead was considered and
  rejected, since that bypasses the user's own permission prompt for every
  matched tool call (`Read`, or `Bash` commands like `rm -rf` and
  `git push --force`).
- Block: `{"hookSpecificOutput": {"hookEventName": "PreToolUse",
  "permissionDecision": "deny", "permissionDecisionReason": "<message>"}}`,
  built with `jq -cn --arg` so paths and messages are escaped, `exit 0`.

`evals/run.sh` treats empty stdout as `allow` and the matching deny envelope
as `block`. The hook accepts `--harness claude|codex|copilot`: Claude and
Codex use Claude-shaped input and `hookSpecificOutput`; Copilot decodes its
camelCase `toolArgs`, including a JSON string, and uses a flat deny object.
Copilot `view_range`, including `[1, -1]`, is treated like Claude `offset` or
`limit`, so it shares the existing offset/limit bypass. The eval fixtures cover
the envelope shapes as well as routing decisions.

The bulk-reader and code-writer skills named their scripts as
`${CLAUDE_PLUGIN_ROOT}/scripts/...`. Copilot does not set that variable in
the agent's shell, so the command exited 127 there. Both skills now name
the script relative to the skill's base directory, which Claude Code and
Copilot both print when they load a skill.

Everything else (the rest of the skill text, the AiKA transport,
the offset/limit bypass, the `head -n 5` parser gap) is unchanged from
upstream and out of scope for this patch. Upstream issues #18 and #20 are not
addressed here. The hook-cwd part of upstream #21 is handled.

## 0.3.0: subagent reads (dotai-4cy)

Bulk-reader now delegates a specific question and paths to a small, fast,
read-only subagent, which returns concise answers with line citations.
Claude uses Agent/Explore/haiku; Copilot uses task/explore/sync and the
small `gpt-5.4-mini` model when exposed, or the built-in explore default.
Codex uses its exposed subagent mechanism,
or targeted and chunked reads when none is available. The main agent
re-reads only the exact cited lines before editing.

Both deny reasons lead with delegation for understanding and questions,
without checking Portal availability. Exact content and edits retain the
chunk instructions introduced in f1491ab. Claude PreToolUse `agent_id`
switches to chunk-only guidance. Copilot 1.0.95 has no subagent identity
in the observed hook input; its shared
reason and every reader prompt say not to delegate again when already the
reader. No assumed Copilot identity field is used.

Deleted `scripts/bulk-read`, its benchmark runner and scenarios, and the
reader mode pin from documentation and transport evals. `scripts/code-write`
and its required AiKA transport remain on Portal. Prerequisites and generated
manifests now describe that split. The earlier note about the rest of the
skill text and transport being unchanged applies to the initial patch only.

Local schema probe: Copilot CLI 1.0.95's `definitions/explore.agent.yaml`
selects `[gpt-5.6-luna, gpt-5.4-mini]` with low reasoning effort and read tools.
The live task probe exposed `agent_type` values explore, task, general-purpose,
rubber-duck, code-review, research, and security-review. It also exposed
`model` (including gpt-5.4-mini), `mode` (sync/background), `context_tier`, and
`reasoning_effort`, in addition to name, description, and prompt. The skill
selects explore and the small model when supported, falling back to explore's
default on versions without that override. Live preToolUse inputs contained
cwd, sessionId, timestamp, toolArgs, and toolName, without a subagent id.
Bead dotai-4cy's close reason records the live-run evidence.
