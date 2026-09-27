### Delegate to Codex

**In plain words:** hand one coding or review job to Codex, a different AI tool, instead of doing it here. A small watcher agent starts the Codex run and tells you how it ended; you read the result yourself and check it against git.

**You own the run.** Claude Code only; skip this playbook on any other harness. The watcher's own steps are `references/codex-watcher-body.md`, which is the whole body of both watchers, and `hooks/codex_watcher_guard.py` locks it to exactly those commands. This page is the owner's half. The watcher prefers `codex-agent`, a dedicated Codex install with its own `CODEX_HOME`, so a run using it never shares the user's interactive Codex session, config, or authentication state.

No installer creates `codex-agent`; create it yourself, once per machine, to get that isolation:

```sh
#!/bin/sh
export CODEX_HOME="$HOME/.codex-agent"
exec "$(command -v codex)" "$@"
```

Without it on `PATH`, the watcher falls back to bare `codex`, sharing your interactive Codex session, config, and authentication state instead of isolating them. Delegation still runs; it just loses the isolation the wrapper buys.

1. Reach for Codex when the unit is one scoped implementation (`pstack:developer-codex`) or one review gate (`pstack:reviewer-codex`). Multi-kind work, tests, search, and orchestration stay on Claude: the watcher holds only Bash, and the run starts with `-c agents.enabled=false`, so Codex does the brief itself and spawns no helpers. Codex already known unavailable this session: spawn plain `pstack:developer` or `pstack:reviewer` instead.
2. Create the run with `scripts/create_agent_run.py` in the `poteto-mode` skill's directory. Give it `--slug`, the task on stdin, and one of these:

   - A writer on a new worktree: `--kind writer --base <commit-ish>`. Put the branch you actually want the writer working from, such as `develop` or `agent/pr2-split`. The script takes `--base` literally instead of inheriting your checkout's branch.
   - A writer continuing an earlier writer run: `--kind writer --worktree <earlier RUN>/worktree`.
   - A reviewer: `--kind reviewer --worktree <tree to review>`.

   The brief's frontmatter is a documented default, and the watcher infers what it lacks. `--model` is optional, and without it Codex uses its default model. To pin one, take it from the plugin's `models.json`, two directories up from the `poteto-mode` skill's own directory and `plugins/pstack/models.json` in the repo (see that skill's Models section): the first `codex` entry of the `feature, refactoring` row for a writer, of `judgment and prose` for a reviewer. The script prints RUN, the run directory. The guard checks every run path against `AGENT_RUNS_DIR` when it is set, so set it as an absolute path in the session environment (on Claude Code, the `env` block of settings). Setting it inline on one command does not reach the hook.
3. Spawn the watcher without `isolation`, always, with exactly this prompt:

   ```
   Your run directory is <RUN>. Read <RUN>/brief.md first and follow it.
   ```

   Runs live under the main checkout, not inside a harness worktree, so `isolation: "worktree"` only adds a checkout nobody uses. Pin the watcher's own model from the `codex watchers` row.
4. Read the reply by key: `fallback`, `command`, `exit code`, then `reason` on a fallback or an optional `inferred` on success. Ignore any other line. The watcher never opens the report and never retypes Codex's output, so those lines are all you get from it. `exit code` is a number, `timeout`, `denied`, or `(none)`.
5. `fallback: none`: open `<RUN>/report.md` yourself, then run `git log` and `git diff <base>..HEAD` in the brief's `worktree`, with `base` from the brief's frontmatter. When the reply has `inferred`, check each guess is what you meant. A commit the report claims counts only when git shows it. No report file at that path despite `fallback: none` means the run failed anyway; treat it as step 6.
6. `fallback: claude` means Codex did not run. Handle it in this order.

   - Append one line with the failure and the reply's `reason` to `<RUN>/progress.md`, so a later pickup sees Codex never ran.
   - Tell the user in your next user-facing reply that Codex did not run for this task and why, even when the Claude fallback then succeeds. A spawner that is itself a subagent puts the failure and reason in its own report instead, so it reaches the top-level agent. A guard `denied` after three tries gets the same report, with the invariant its `reason` names.
   - When the `reason` is the run itself, such as no run directory in the prompt, a writer with no worktree inside the runs root, or a run created under a different `AGENT_RUNS_DIR` than the hook sees, create a fresh run with the fix and spawn a fresh watcher on it. A brief is read-only, so never edit it and never send a Claude fallback into the broken run.
   - Every other failure takes the Claude fallback on the same run. Spawn `pstack:developer` or `pstack:reviewer` with the same prompt and without `isolation`. It reads `progress.md` and continues from there. When `exit code: timeout` sent you here, confirm no run still holds the brief's worktree before the fallback writer touches it. A plain `pgrep -af "codex exec"` fails two ways: it can self-match an ancestor process whose own command line carries that text, and it false-positives on any unrelated process that does too. Key the check to `<worktree>` instead, since `-C <worktree>` survives verbatim into the live process's argv once `codex-agent` execs the codex binary: `pgrep -af -- "codex exec.*-C <worktree>( |$)"`. Nothing found means no run still holds it.

   A correct brief that the guard still denies means the guard and this playbook disagree, which is a bug in one of them.
7. Review the diff yourself and write your own summary. Codex's report is evidence, not your verdict.

**Reply:** your own summary of the diff, the run's report path, and the git evidence you checked the report against.
