# Codex workers from Claude Code

Use this file only when Claude Code is the harness and you hand a task to the Codex CLI as an outside worker. When pstack itself runs inside Codex, this file does not apply. Read [`codex-tools.md`](codex-tools.md) instead, and use `spawn_agent`.

A Codex worker is a delegate. It runs a brief and edits code itself, the same as a `pstack:poteto-agent` code delegate.

## Scope the access

Before you write the brief, list what the worker needs:

- The folders it writes. Its worktree is always one. Add others only when the task needs them.
- Whether it needs network access.
- Whether its checks write temp files, as most test and build tools do.

Turn that list into sandbox flags. `<scope>` in the commands below stands for these flags:

```bash
-c 'sandbox_mode="workspace-write"' -c 'sandbox_workspace_write.writable_roots=["<other-folder>"]' -c 'sandbox_workspace_write.network_access=false' -c 'sandbox_workspace_write.exclude_slash_tmp=true' -c 'sandbox_workspace_write.exclude_tmpdir_env_var=true' -c 'approval_policy="on-request"' -c 'approvals_reviewer="auto_review"'
```

- The worker can write only to its worktree and the folders in `writable_roots`. Use absolute paths, and `[]` when it writes only to its worktree. The sandbox does not limit reads.
- Set `network_access` to `true` when it needs network access.
- Set both `exclude_*` keys to `false` when its checks write temp files.
- Codex keeps every `.git` folder read-only, so a commit asks to leave the sandbox. The Codex auto reviewer approves or refuses that request. Do not add a `.git` folder to `writable_roots`.
- Use `sandbox_mode="danger-full-access"` only when the task cannot run in the sandbox. Tell the user in your reply that the run had full access.

Do not add guard hooks or wrapper scripts around the run.

## Spawn

1. Give each writer its own worktree or branch (**principle-separate-before-serializing-shared-state**).
2. Write the brief to a file. Start it with "Load the poteto-mode skill." Include the goal, the done state, the checks to run, and the branch to commit on. The worker commits its own work.
   Keep `<run-dir>` outside the worktree, so the run files stay out of the diff.
3. Start the run with the Bash tool and `run_in_background: true`:

   ```bash
   rm -f <run-dir>/exit-code; codex exec --json -C <worktree> <scope> -o <run-dir>/last-message.md - < <run-dir>/brief.md > <run-dir>/events.jsonl; echo $? > <run-dir>/exit-code
   ```

Omit `-m` to use the Codex default model. Pass `-m` only when the task's difficulty needs a different Codex model.

## Monitor

- Claude Code starts a new turn when the background command exits. Do not poll.
- To watch a run while it works, point the `Monitor` tool at its events file. Each line is one JSON event. The first is `thread.started` with the `thread_id`. Each finished step is `item.completed`. The end of a turn is `turn.completed` or `turn.failed`.
- The final answer is in `last-message.md`.
- A run failed if `exit-code` is not `0`, the last `turn.*` event in its events file is not `turn.completed`, or the worktree has uncommitted changes or no commit since the base it branched from. A refused commit still ends with `turn.completed`. Tell the user in your next reply that Codex did not do the task, and why.

## Follow up

The **Fresh subagents by default** rule in [Subagents](../SKILL.md#subagents) applies. A fresh run in the same worktree keeps its files and uncommitted changes. Resume only when the follow-up needs the thread's conversation and that context is too costly to put in a brief:

```bash
rm -f <run-dir>/exit-code; (cd <worktree> && codex exec resume --json <scope> -o <run-dir>/last-message.md <thread_id> - < <run-dir>/follow-up.md > <run-dir>/events-resume-<n>.jsonl; echo $? > <run-dir>/exit-code)
```

`resume` has no `-C` flag, so it uses the current directory as its workdir. It does not keep the original sandbox, so pass the same `<scope>` again.

## Review

The independent review is a fresh Claude subagent. Never count the Codex run's own report as the review.

## Orchestrate

The Orchestrate drain loop reads `Agent` notifications. Inside that playbook, spawn a background `pstack:poteto-agent` whose brief is to run one Codex worker as above and return the run's result. The wrapper starts the run in the background. Then it blocks with a foreground Bash call, `until [ -s <run-dir>/exit-code ]; do sleep 10; done`, with `timeout: 600000`, and repeats that call until the file exists. It never ends its turn while the run is live. `Monitor` does not block, so the wrapper does not use it to wait. The review is the unit's verifier, not a diff read inside a drain. Outside Orchestrate, start the run with the Bash tool directly.
