# shunt plugin source

Vendored from Spotify's `portal-ai-plugins` marketplace.

- Source: https://github.com/spotify/portal-ai-plugins/tree/main/plugins/shunt
- Revision: `e14bdb1` (shunt's last touch on that repo; repo main is `3c24ca3`)
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

`evals/run.sh` was updated to match: empty stdout is `allow`,
`hookSpecificOutput.permissionDecision == "deny"` is `block`. The eval
fixtures (`evals/hook-evals.json`, `evals/bash-hook-evals.json`) are
untouched, since `expected_decision` names the outcome, not the wire shape.

Everything else (the bulk-reader/code-writer skills, the AiKA transport,
the offset/limit bypass, the `head -n 5` parser gap) is unchanged from
upstream and out of scope for this patch. Upstream issues #18, #20, #21 are
not addressed here.
