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

Both read guards resolve relative paths from the session cwd before allowing
files under an exact `.handoffs` or `handoffs` directory segment through,
regardless of line count. Agents need the full handoff to resume work.
This exception covers Read/view and `cat`, `head`, `tail`, `less`, and `more`
on Claude Code, Codex, and Copilot CLI. A filename such as `handoffs.txt` or
a directory such as `myhandoffs` still follows the size guard. The eval runner
creates parent directories for nested fixtures to exercise these paths.

The bulk-reader and code-writer skills named their scripts as
`${CLAUDE_PLUGIN_ROOT}/scripts/...`. Copilot does not set that variable in
the agent's shell, so the command exited 127 there. Both skills now name
the script relative to the skill's base directory, which Claude Code and
Copilot both print when they load a skill.

Everything else (the rest of the skill text, the AiKA transport,
the offset/limit bypass, the `head -n 5` parser gap) is unchanged from
upstream and out of scope for this patch. Upstream issues #18 and #20 are not
addressed here. The hook-cwd part of upstream #21 is handled.
