### Delegate to Codex

**In plain words:** hand one coding or review job to Codex, a different AI tool, instead of doing it here. A small watcher agent runs one Codex session on a bead and tells you how it ended; you read the bead and check it against git.

**You own the run.** Claude Code only; skip this playbook on any other harness. The watcher agents (`developer-codex`, `reviewer-codex`) hold only Bash, Write, SendMessage, and Monitor. A watcher runs every `bd` command raw, because Codex's sandbox cannot open the bead store. It builds Codex's prompt from `bd show <id> --json`, sends it on stdin to a detached Codex process, waits on its exit-code file with Monitor, and reads Codex's last message back from a temp file. It never does any part of the task itself. This page is the owner's half. The bead loop itself is in [`references/beads-work-loop.md`](../references/beads-work-loop.md).

Run plain `codex`. The watchers share the user's own `~/.codex`: login, config, plugins, and `codex resume` history, all with the interactive session. A missing login ends the run with `fallback: claude` and a `reason` that names `codex login`.

A writer commits its own work. Codex's `workspace-write` sandbox keeps every `.git` read-only by default. The watcher opens it for one run with `--add-dir` on the worktree's git-common `objects`, `refs`, and `logs` directories plus its own gitdir, never the whole `.git`, which would also make `config` and `hooks` writable. This lets a writer move refs for any branch, not only its own. The plugin's `scripts/codex_writer_grants.py` prints those grants. It refuses a main checkout, whose gitdir is the whole `.git`, so a writer runs only in a linked worktree, and the watcher replies `fallback: claude` otherwise. Every git command the watcher runs after Codex carries `-c core.hooksPath=/dev/null`, so a hook in a path Codex could write, such as a `core.hooksPath` inside the worktree, never runs outside the sandbox. A reviewer runs `-s read-only` in the worktree and writes nothing.

1. Reach for Codex when the unit is one scoped implementation (`pstack:developer-codex`) or one review gate (`pstack:reviewer-codex`). Multi-kind work, tests, search, and orchestration stay on Claude. Every run starts with `-c agents.enabled=false`, so Codex does the task itself and spawns no helpers. A plugin `PreToolUse` hook (`hooks/codex_exec_no_agents.py`) adds that flag to any `codex exec` on any Bash call that is missing it, watcher or not. If Codex is already known unavailable this session, spawn plain `pstack:developer` or `pstack:reviewer` instead.
2. Create the bead and the worktree as poteto-mode's Agent runs paragraph says. Put the scope in the bead's description and the done-when in `--acceptance`, because Codex sees only the bead's title, description, and acceptance. The watcher picks the Codex model from the plugin's `models.json`: the first `codex` entry of the `feature, refactoring` row for a writer, and of `judgment and prose` for a reviewer.
3. Spawn the watcher without `isolation`, with the same prompt a Claude agent gets:

   ```
   Claim bead <id> as developer-<id>. Work in <worktree>.
   ```

   For an Orchestrate unit, append the stop suffix:

   ```
   Claim bead <id> as developer-<id>. Work in <worktree>. Stop at stage=built.
   ```

   ```
   Review bead <id> at <SHA> in <worktree>.
   ```

   Use the actor `developer-<id>` for a Codex writer, so a Claude fallback with the same prompt holds the same claim. Pin the watcher's own model from the `codex watchers` row (its frontmatter already carries `model: sonnet`).
4. Read the reply by key: `fallback`, `command`, `exit code`, then `commit` from a writer, `verdict` from a reviewer, and `reason` on a fallback. Ignore any other line. `exit code` is a number or `(none)`. A long run sends no interim message. The watcher's one reply arrives when Codex exits.
5. `fallback: none`: run `beads:show` for the close reason and `beads:comments` for the verdict. A writer prompt that ends with `Stop at stage=built.` leaves the bead open, and its `ready at <SHA> on <branch>` comment takes the place of the close reason. Then run `git log --grep '(<id>)'` and `git diff <base>..<SHA>` in the worktree. A commit the close reason claims counts only when git shows it.
6. `fallback: stop`: no agent can start. Fix the cause the `reason` names, such as a malformed prompt or a bead another actor holds, then spawn a fresh watcher.
7. `fallback: claude` means Codex did not finish. Handle it in this order.

   - Record it on the bead, so a later pickup sees it. Write `codex did not finish: <reason>` to a `mktemp` file with the Write tool and add it with `beads:comments` (`bd comment <id> --file <path>`), because the reason can carry text the shell would run.
   - Tell the user in your next user-facing reply that Codex did not run for this task and why, even when the Claude fallback then succeeds. A spawner that is itself a subagent puts the failure and reason in its own report instead, so it reaches the top-level agent.
   - Before a fallback writer touches the worktree, confirm no Codex run still holds it. A plain `pgrep -af "codex exec"` fails two ways: it can self-match an ancestor process whose own command line carries that text, and it false-positives on any unrelated process that does too. Key the check to `<worktree>` instead, since the watcher passes `-C <worktree>` verbatim in the live `codex exec` process's argv: `pgrep -af -- "codex exec.*-C <worktree>( |$)"`. Nothing found means no run still holds it.
   - Spawn `pstack:developer` or `pstack:reviewer` without `isolation`, with the prompt the watcher got. A writer's claim succeeds again for the same actor, and the writer reads the bead and the worktree to continue from what Codex left.
8. Review the diff yourself and write your own summary. Codex's close reason or verdict is evidence, not your verdict.

**Reply:** your own summary of the diff, the bead ID with its close reason or verdict, and the git evidence you checked them against.
