---
name: codex-watcher
description: Start and wait for one scoped Codex writer or native review through the Claude Code watcher adapters. Use for a watcher request, not for task implementation or fallback.
---

# Start one Codex run

This is the Claude Code adapter for [Delegate to Codex](../poteto-mode/playbooks/delegate-to-codex.md).
The coordinator maps implementation to `pstack:developer-codex` and native review to `pstack:reviewer-codex`.
Both watchers use `model: sonnet` and the `Bash` and `Monitor` tools.
The plugin-level PreToolUse guard uses the documented [agent_type field](https://code.claude.com/docs/en/hooks#common-input-fields) to restrict their tool calls.
It allows other callers without output.

The input is one complete line in one of these forms.

```text
Claim bead <id> as developer-<id>. Work in <absolute worktree>.
Claim bead <id> as developer-<id>. Work in <absolute worktree>. Stop at stage=built.
Review bead <id> at <SHA> in <absolute worktree>.
```

Append ` Grant: <absolute path> <absolute path>` for extra grants.
The grant suffix must come last.
Each grant must exist and contain no spaces.
The builder validates review grants but does not give native review write access.

## Run the watcher

1. Resolve the plugin root from this skill's directory, two directories up.
   Run the builder once through `Bash`, with the request unchanged in a quoted heredoc.
   Replace `<builder>` with the absolute `scripts/prepare_codex_run.py` path.
   Use the path without quotes when it contains only shell-safe characters.
   Otherwise, use shell single quotes and escape each embedded single quote as `'"'"'`.

   ```sh
   python3 <builder> --launch <<'PSTACK_REQUEST'
   <request line>
   PSTACK_REQUEST
   ```

2. If the output contains `PSTACK_CODEX_STOP`, end the turn with no text.
   Do the same if the tool fails or returns no run directory.
   The builder launches nothing after a preparation failure.
   Do no task work, retry, repair, or fallback.

3. Otherwise, copy the run directory from stdout.
   Wait with `Monitor`, `timeout_ms: 1800000`, and this exact command.
   Apply the same shell quoting to `<run dir>/codex.jsonl` as to the builder path.

   ```sh
   until grep -qs '"pstack":"codex exited"' <run dir>/codex.jsonl; do sleep 5; done; echo codex exited
   ```

4. If Monitor times out without an event, re-arm the same Monitor command.
   The exit marker covers both successful and failed Codex exits.
   When Monitor reports the event, end the turn with no text.

The guard is stateless.
It allows only the exact builder command with a quoted request and the fixed wait under the Codex run state directory.
It denies all other tools and commands, including task edits and manual Codex calls.
The coordinator reads the run files and owns failure handling.

## Check a live run

The coordinator can run the preserved writer and native-review fixture with this command.
Use the claimed owner's bead environment.

```sh
IMPLEMENTATION_BEAD=<owner bead> python3 <plugin root>/scripts/check_codex_watchers.py
```

The check uses a separate bead store and sends owner heartbeats during each bounded watcher call.
It verifies a local built commit, no push, a native pass, and unchanged Git after review.
It preserves the fixture and logs under the project's `.nikki-agents/` directory on success or failure.
