### Delegate to Codex

**In plain words:** hand one coding or review job to Codex, a different AI tool, instead of doing it here. A small watcher agent starts the Codex run and tells you how it ended; you read the result yourself and check it against git.

**You own the run.** Claude Code only; skip this playbook on any other harness. The watcher agents run one command, `pstack-codex-run <RUN>`, from the plugin's `bin/` directory, which Claude Code puts on the Bash tool's PATH while the plugin is enabled. The command reads the brief's frontmatter, checks RUN and the worktree against the runs root, builds the `codex exec` command, and prints the reply lines. `hooks/codex_watcher_guard.py` denies a watcher every other call. This page is the owner's half.

`pstack-codex-run` sets `CODEX_HOME` for Codex to `$PSTACK_CODEX_HOME` when that is set, else `~/.codex-agent`. A separate home keeps agent runs out of the user's interactive Codex session, config, and login. It needs its own login, once per machine:

```sh
CODEX_HOME=~/.codex-agent codex login
```

A missing login ends each run with `fallback: claude` and a `reason` that names this command.

A writer commits its own work. Codex's `workspace-write` sandbox keeps every `.git` read-only, so `pstack-codex-run` links `bin/pstack-codex-writer.rules` into `$CODEX_HOME/rules/` before each writer run. That rule lets exactly `git add ...` and `git commit ...` run outside the sandbox without a prompt. Every other git command, including `git -C <dir> commit` and `git -c <key>=<value> commit`, stays inside the sandbox and cannot write `.git`. A reviewer runs with `-s read-only --ignore-rules`, so no rule applies to it.

1. Reach for Codex when the unit is one scoped implementation (`pstack:developer-codex`) or one review gate (`pstack:reviewer-codex`). Multi-kind work, tests, search, and orchestration stay on Claude. The watcher holds only Bash, and the run starts with `-c agents.enabled=false`, so Codex does the brief itself and spawns no helpers. Codex already known unavailable this session: spawn plain `pstack:developer` or `pstack:reviewer` instead.
2. Create the run with `scripts/create_agent_run.py` in the `poteto-mode` skill's directory. Give it `--slug`, the task on stdin, and one of these:

   - A writer on a new worktree: `--kind writer --base <commit-ish>`. Put the branch you actually want the writer working from, such as `develop` or `agent/pr2-split`. The script takes `--base` literally instead of inheriting your checkout's branch.
   - A writer continuing an earlier writer run: `--kind writer --worktree <earlier RUN>/worktree`.
   - A reviewer: `--kind reviewer --worktree <tree to review>`.

   `pstack-codex-run` reads `kind` and `worktree` from the brief's frontmatter and refuses a brief that lacks either. A writer's worktree must sit inside the runs root and have a `.git`. `--model` is optional, and without it Codex uses its default model. To pin one, take it from the plugin's `models.json`, two directories up from the `poteto-mode` skill's own directory and `plugins/pstack/models.json` in the repo (see that skill's Models section): the first `codex` entry of the `feature, refactoring` row for a writer, of `judgment and prose` for a reviewer. The script prints RUN, the run directory. `pstack-codex-run` checks every run path against `AGENT_RUNS_DIR` when it is set, so set it as an absolute path in the session environment (on Claude Code, the `env` block of settings). Setting it inline on one command does not reach the watcher's Bash call.

   A writer's task must tell Codex to commit its work in the worktree. The rules file allows `git add` and `git commit`, so a commit that fails is a bug to report, not a step to note and skip.
3. Spawn the watcher without `isolation`, always, with exactly this prompt:

   ```
   Your run directory is <RUN>. Read <RUN>/brief.md first and follow it.
   ```

   Runs live under the main checkout, not inside a harness worktree, so `isolation: "worktree"` only adds a checkout nobody uses. Pin the watcher's own model from the `codex watchers` row.
4. Read the reply by key: `fallback`, `command`, `exit code`, then `reason` on a fallback. Ignore any other line. The watcher never opens the report, and `pstack-codex-run` sends Codex's own output to `<RUN>/codex-exec.log`, so those lines are all you get from it. `exit code` is a number, `timeout`, `denied`, or `(none)`.
5. `fallback: none`: open `<RUN>/report.md` yourself, then run `git log` and `git diff <base>..HEAD` in the brief's `worktree`, with `base` from the brief's frontmatter. A commit the report claims counts only when git shows it. No report file at that path despite `fallback: none` means the run failed anyway; treat it as step 6.
6. `fallback: claude` means Codex did not run. Handle it in this order.

   - Append one line with the failure and the reply's `reason` to `<RUN>/progress.md`, so a later pickup sees Codex never ran.
   - Tell the user in your next user-facing reply that Codex did not run for this task and why, even when the Claude fallback then succeeds. A spawner that is itself a subagent puts the failure and reason in its own report instead, so it reaches the top-level agent. A guard `denied` gets the same report, with its `reason`.
   - When the `reason` is the run itself, such as no run directory in the prompt, a brief without `kind` or `worktree`, a writer with no worktree inside the runs root, or a run created under a different `AGENT_RUNS_DIR` than `pstack-codex-run` sees, create a fresh run with the fix and spawn a fresh watcher on it. A brief is read-only, so never edit it and never send a Claude fallback into the broken run.
   - Every other failure takes the Claude fallback on the same run. Spawn `pstack:developer` or `pstack:reviewer` with the same prompt and without `isolation`. It reads `progress.md` and continues from there. When `exit code: timeout` sent you here, confirm no run still holds the brief's worktree before the fallback writer touches it. A plain `pgrep -af "codex exec"` fails two ways: it can self-match an ancestor process whose own command line carries that text, and it false-positives on any unrelated process that does too. Key the check to `<worktree>` instead, since `pstack-codex-run` passes `-C <worktree>` verbatim in the live `codex exec` process's argv: `pgrep -af -- "codex exec.*-C <worktree>( |$)"`. Nothing found means no run still holds it.

   A correct run that `pstack-codex-run` still refuses, or a guard denial of `pstack-codex-run <RUN>` itself, means the command, the guard, and this playbook disagree. That is a bug in one of them.
7. Review the diff yourself and write your own summary. Codex's report is evidence, not your verdict.

**Reply:** your own summary of the diff, the run's report path, and the git evidence you checked the report against.
