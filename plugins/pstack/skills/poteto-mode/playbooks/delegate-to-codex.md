### Delegate to Codex

**In plain words:** hand one coding or review job to Codex, a different AI tool, instead of doing it here. A small watcher agent runs one Codex session and tells you how it ended; you read the result yourself and check it against git.

**You own the run.** Claude Code only; skip this playbook on any other harness. The watcher agents (`developer-codex`, `reviewer-codex`) hold only Bash, Write, and SendMessage. Each reads `<RUN>/brief.md`'s frontmatter for `kind`, `worktree`, `base`, `model`, and `mode`, runs one `codex exec` (or `codex review` for `mode: diff-review`), and prints the reply lines below. They never read the rest of the brief, never open the report, and never do any part of the task themselves. This page is the owner's half.

Run plain `codex`. Agent runs share the user's own `~/.codex`: login, config, plugins, and `codex resume` history, all with the interactive session. A missing login ends the run with `fallback: claude` and a `reason` that names `codex login`.

A writer commits its own work. Codex's `workspace-write` sandbox keeps every `.git` read-only by default; the watcher lifts that narrowly for one run with `--add-dir` on the worktree's git-common `objects`, `refs`, and `logs` directories plus its own gitdir, never the whole `.git` (that would also make `config` and `hooks` writable). This lets a writer move refs for any branch, not only its own; the user accepted that trade over an execpolicy rules file. A reviewer runs `-s workspace-write --ignore-rules` rooted at its own run directory, so it can write only there and no rule applies to it. A diff-review reviewer runs `-s read-only` rooted at the worktree and writes nothing; the watcher redirects its stdout into `agent-report.md`.

1. Reach for Codex when the unit is one scoped implementation (`pstack:developer-codex`) or one review gate (`pstack:reviewer-codex`). Multi-kind work, tests, search, and orchestration stay on Claude. The run starts with `-c agents.enabled=false`, so Codex does the brief itself and spawns no helpers; a plugin `PreToolUse` hook (`hooks/codex_exec_no_agents.py`) adds that flag to any `codex exec` on any Bash call that is missing it, watcher or not, as a second line of defense. Codex already known unavailable this session: spawn plain `pstack:developer` or `pstack:reviewer` instead.
2. Create the run with `scripts/create_agent_run.py` in the `poteto-mode` skill's directory, the same as any other agent run. Give it `--slug`, the task on stdin, and one of these:

   - A writer on a new worktree: `--kind writer --base <commit-ish>`. Put the branch you actually want the writer working from, such as `develop` or `agent/pr2-split`. The script takes `--base` literally instead of inheriting your checkout's branch.
   - A writer continuing an earlier writer run: `--kind writer --worktree <earlier RUN>/worktree`.
   - A reviewer: `--kind reviewer --worktree <tree to review>`.
   - A diff-review reviewer: `--kind reviewer --mode diff-review --worktree <tree to review> --base <commit-ish to diff against>`. Codex runs its built-in `codex review --base <base>` on the worktree, which cannot take a prompt. It never sees the brief body, so use this only for a generic "is this branch's diff correct" gate. A gate that checks the diff against a brief or spec stays a plain reviewer run.

   Always pass `--model`, because without it Codex falls back to the user's `~/.codex` default. Take it from the plugin's `models.json`, two directories up from the `poteto-mode` skill's own directory and `plugins/pstack/models.json` in the repo (see that skill's Models section): the first `codex` entry of the `feature, refactoring` row for a writer, of `judgment and prose` for a reviewer. The script prints RUN, the run directory.
3. Spawn the watcher without `isolation`, always, with exactly this prompt:

   ```
   Your run directory is <RUN>.
   ```

   Runs live under the main checkout, not inside a harness worktree, so `isolation: "worktree"` only adds a checkout nobody uses. Pin the watcher's own model from the `codex watchers` row (its frontmatter already carries `model: sonnet`).
4. Read the reply by key: `fallback`, `command`, `exit code`, then `reason` on a fallback. Ignore any other line. The watcher sends Codex's own output to `<RUN>/codex-exec.log`, so those lines are all you get from it. `exit code` is a number or `(none)`. `fallback: pending` arrives as a message, not as the watcher's reply, and means Codex outlived the watcher's Bash timeout and is still running in the background. Wait for the watcher's reply, which carries the final lines, and never fall back on `pending`.
5. `fallback: none`: open `<RUN>/agent-report.md` and `<RUN>/decisions.tsv` yourself (a diff-review run has only `agent-report.md`, the review text Codex printed, and no `decisions.tsv`), then run `git log` and `git diff <base>..HEAD` in the brief's `worktree`, with `base` from the brief's frontmatter. A commit the report claims counts only when git shows it. No report file at that path despite `fallback: none` means the run failed anyway; treat it as step 6.
6. `fallback: claude` means Codex did not run. Handle it in this order.

   - Append one line with the failure and the reply's `reason` to `<RUN>/progress.md`, so a later pickup sees Codex never ran.
   - Tell the user in your next user-facing reply that Codex did not run for this task and why, even when the Claude fallback then succeeds. A spawner that is itself a subagent puts the failure and reason in its own report instead, so it reaches the top-level agent.
   - When the `reason` is the run itself, such as no run directory in the prompt or a brief without `kind` or `worktree`, create a fresh run with the fix and spawn a fresh watcher on it. A brief is read-only, so never edit it and never send a Claude fallback into the broken run.
   - Every other failure takes the Claude fallback on the same run. Spawn `pstack:developer` or `pstack:reviewer` without `isolation`, with exactly this prompt:

     ```
     Your run directory is <RUN>. Read <RUN>/brief.md first and follow it.
     ```

     It reads `progress.md` and continues from there. Before that fallback writer touches the worktree, confirm no Codex run still holds it. A plain `pgrep -af "codex exec"` fails two ways: it can self-match an ancestor process whose own command line carries that text, and it false-positives on any unrelated process that does too. Key the check to `<worktree>` instead, since the watcher passes `-C <worktree>` verbatim in the live `codex exec` process's argv: `pgrep -af -- "codex exec.*-C <worktree>( |$)"`. Nothing found means no run still holds it.
7. Review the diff yourself and write your own summary. Codex's report is evidence, not your verdict.

**Reply:** your own summary of the diff, the run's report path, its `decisions.tsv`, and the git evidence you checked the report against.
