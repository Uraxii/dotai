# Codex workers from Claude Code

Use this file only when Claude Code is the harness and Codex is an outside worker. Do not use this file when pstack runs inside Codex. For that case, read [`codex-tools.md`](codex-tools.md) and use `spawn_agent`.

A Codex worker is a delegate. It does the brief and edits the code. It is the same as a `pstack:poteto-agent` code delegate.

## Scope the access

Before you write the brief, make a list of what the worker needs:

- The folders that the worker writes to. Its worktree is always on the list. Add other folders only when the task needs them.
- Network access, if the task needs it.
- Temp files outside the worktree, if the checks write them to `/tmp` or `$TMPDIR`. Many test tools and build tools do this.

Put the list into sandbox flags. In the commands below, `<scope>` is these flags:

```bash
-c 'sandbox_mode="workspace-write"' -c 'sandbox_workspace_write.writable_roots=["<other-folder>"]' -c 'sandbox_workspace_write.network_access=false' -c 'sandbox_workspace_write.exclude_slash_tmp=true' -c 'sandbox_workspace_write.exclude_tmpdir_env_var=true' -c 'approval_policy="on-request"' -c 'approvals_reviewer="auto_review"'
```

- The worker can write only to its worktree and to the folders in `writable_roots`. The sandbox does not limit reads.
- Use absolute paths in `writable_roots`. If the worker writes only to its worktree, use `[]`.
- If the worker needs network access, set `network_access` to `true`.
- If the checks write temp files to `/tmp` or `$TMPDIR`, set the two `exclude_*` keys to `false`.
- Do not add a `.git` folder to `writable_roots`. Codex keeps all `.git` folders read-only.
- A commit must go outside the sandbox. The Codex auto reviewer approves or refuses each commit.
- The events file has no approval event. A commit shows only as a `command_execution` item that completed or failed.
- Use `sandbox_mode="danger-full-access"` only when the task cannot run in the sandbox. If you use it, tell the user that the run had full access.

Do not add guard hooks or wrapper scripts to the run.

## Start the run

1. Give each worker its own worktree or branch (**principle-separate-before-serializing-shared-state**).
2. Make a `<run-dir>` outside the worktree. This keeps the run files out of the diff.
3. Write the brief to `<run-dir>/brief.md`. Start the brief with "Load the poteto-mode skill."
4. In the brief, give the goal, the done state, the checks, and the branch for the commit. The worker commits its own work.
5. Start the run with the Bash tool and `run_in_background: true`:

   ```bash
   rm -f <run-dir>/exit-code; codex exec --json -C <worktree> <scope> -o <run-dir>/last-message.md - < <run-dir>/brief.md > <run-dir>/events.jsonl; echo $? > <run-dir>/exit-code
   ```

To use the Codex default model, do not use `-m`. Use `-m` only when the task is too difficult for the default model.

## Monitor the run

- When the background command stops, Claude Code starts a new turn. Do not poll.
- To see the run while it works, use the `Monitor` tool on the events file. Each line is one JSON event.
- The first event is `thread.started`. It has the `thread_id`.
- Each completed step is an `item.completed` event. Its `item.type` can be `command_execution`, `file_change`, `agent_message`, or a different type. The end of a turn is `turn.completed` or `turn.failed`.
- The last message from the worker is in `last-message.md`.

The run failed if one or more of these conditions are true:

- The value in `exit-code` is not `0`.
- The last `turn.*` event in the events file is not `turn.completed`.
- A tracked file in the worktree has changes that are not committed. Untracked caches and agent notes are not a failure.
- The branch has no commit after its base.
- An untracked file that git does not ignore is part of the task.

A refused commit can also end with `turn.completed`, so do all the checks. If the run failed, tell the user in your next reply. Say that Codex did not do the task, and say why.

## Send a follow-up

The **Fresh subagents by default** rule in [Subagents](../SKILL.md#subagents) applies. A fresh run in the same worktree keeps the files and the changes that are not committed. Resume only if the follow-up needs the conversation of the thread, and a brief cannot hold it at low cost.

```bash
rm -f <run-dir>/exit-code; (cd <worktree> && codex exec resume --json <scope> -o <run-dir>/last-message.md <thread_id> - < <run-dir>/follow-up.md > <run-dir>/events-resume-<n>.jsonl; echo $? > <run-dir>/exit-code)
```

`resume` has no `-C` flag. It uses the current directory as its workdir. `resume` does not keep the sandbox of the first run, so give the same `<scope>` again.

## Review the work

The review is a separate step. Start it after the work run stops. Any harness can do the review. The reviewer must be a fresh agent that did not write the change. Use one of these reviewers:

- A fresh Claude subagent. Follow [Subagents](../SKILL.md#subagents).
- A separate Codex review run that is read-only. Start it from the worktree with the Bash tool and `run_in_background: true`. This run reads the diff. It does not do the checks.

  ```bash
  rm -f <run-dir>/review-exit-code; (cd <worktree> && codex exec review --json -c 'sandbox_mode="read-only"' --base <base-branch> -o <run-dir>/review.md > <run-dir>/review-events.jsonl; echo $? > <run-dir>/review-exit-code)
  ```

  The findings are in `review.md`. The review run failed if `review-exit-code` is not `0`. It also failed if the last `turn.*` event in `review-events.jsonl` is not `turn.completed`.

Outside Orchestrate, Codex can review the work of Codex. Inside Orchestrate, the reviewer must use a different model family from the worker. If no review completes, keep the gate closed. Follow [Subagents](../SKILL.md#subagents).

Do not use the report of the worker as the review. The auto reviewer that approves a commit controls only sandbox access. It does not review the code.

## Use a worker in Orchestrate

The Orchestrate drain loop reads only `Agent` notifications. In that playbook, spawn a background `pstack:poteto-agent` as a wrapper. In the brief, tell the wrapper to start one Codex worker as this file tells you. Also tell it to return the result of each failure check and the text of `last-message.md`.

1. The wrapper starts the run in the background.
2. The wrapper waits with a foreground Bash call and `timeout: 600000`:

   ```bash
   until [ -s <run-dir>/exit-code ]; do sleep 10; done
   ```

3. If the call stops before `exit-code` exists, the wrapper does the call again.
4. The wrapper does not end its turn while the run continues.

Do not use the `Monitor` tool to wait. `Monitor` does not block. The review is the verifier of the unit. The verifier is a separate unit, and it uses a different model family from the worker. Do not read the diff inside a drain.

Outside Orchestrate, start the run directly with the Bash tool.
