# Codex workers from Claude Code

Use this file only when Claude Code is the harness and you hand a task to the Codex CLI as an outside worker. When pstack itself runs inside Codex, this file does not apply. Read [`codex-tools.md`](codex-tools.md) instead, and use `spawn_agent`.

A Codex worker is a delegate. It runs a brief and edits code itself, the same as a `pstack:poteto-agent` code delegate.

## Spawn

1. Give each writer its own worktree or branch (**principle-separate-before-serializing-shared-state**).
2. Write the brief to a file. Start it with "Load the poteto-mode skill." Include the goal, the done state, the checks to run, and whether to commit.
   Keep `<run-dir>` outside the worktree, so the run files stay out of the diff.
3. Start the run with the Bash tool and `run_in_background: true`:

   ```bash
   rm -f <run-dir>/exit-code; codex exec --json -C <worktree> -s danger-full-access -o <run-dir>/last-message.md - < <run-dir>/brief.md > <run-dir>/events.jsonl; echo $? > <run-dir>/exit-code
   ```

Grant the access the task needs in the spawn call. Do not add guard hooks or wrapper scripts around the run. Omit `-m` to use the Codex default model. Pass `-m` only when the task's difficulty needs a different Codex model.

## Monitor

- Claude Code starts a new turn when the background command exits. Do not poll.
- To watch a run while it works, point the `Monitor` tool at its events file. Each line is one JSON event. The first is `thread.started` with the `thread_id`. Each finished step is `item.completed`. The end of a turn is `turn.completed` or `turn.failed`.
- The final answer is in `last-message.md`.
- A run failed if `exit-code` is not `0`, or the last `turn.*` event in its events file is not `turn.completed`. Tell the user in your next reply that Codex did not do the task, and why.

## Follow up

The **Fresh subagents by default** rule in [Subagents](../SKILL.md#subagents) applies. A fresh run in the same worktree keeps its files and uncommitted changes. Resume only when the follow-up needs the thread's conversation and that context is too costly to put in a brief:

```bash
rm -f <run-dir>/exit-code; (cd <worktree> && codex exec resume --json -c 'sandbox_mode="danger-full-access"' -o <run-dir>/last-message.md <thread_id> - < <run-dir>/follow-up.md > <run-dir>/events-resume-<n>.jsonl; echo $? > <run-dir>/exit-code)
```

`resume` has no `-C` or `-s` flag. It uses the current directory as its workdir. It does not keep the original sandbox unless you set `sandbox_mode` again.

## Review

The independent review is a fresh Claude subagent. Never count the Codex run's own report as the review.

## Orchestrate

The Orchestrate drain loop reads `Agent` notifications. Inside that playbook, spawn a background `pstack:poteto-agent` whose brief is to run one Codex worker as above and return the run's result. The wrapper starts the run in the background. Then it blocks with a foreground Bash call, `until [ -s <run-dir>/exit-code ]; do sleep 10; done`, with `timeout: 600000`, and repeats that call until the file exists. It never ends its turn while the run is live. `Monitor` does not block, so the wrapper does not use it to wait. The review is the unit's verifier, not a diff read inside a drain. Outside Orchestrate, start the run with the Bash tool directly.
