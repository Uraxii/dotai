### Delegate to Codex

**In plain words:** hand one coding or review job to Codex, a different AI tool, instead of doing it here. A small watcher agent launches one Codex session on a bead and waits for it to exit; Codex does the bead and git work itself, and you read the bead and check it against git.

**You own the run.** Claude Code only; skip this playbook on any other harness. The watcher agents (`developer-codex`, `reviewer-codex`) hold only Bash and Monitor and run on Haiku. A watcher pipes its spawn prompt to `scripts/prepare_codex_run.py`, launches the `run.sh` the script wrote, waits with Monitor until Codex exits, and ends its turn with no reply. Codex claims the bead, sends heartbeats, commits, pushes, comments, sets the stage, and closes, all inside its sandbox. This page is the owner's half. The bead loop itself is in [`references/beads-work-loop.md`](../references/beads-work-loop.md).

Run plain `codex`. The runs share the user's own `~/.codex`: login, config, plugins, and `codex resume` history, all with the interactive session. A run with no login leaves the bead unclaimed and the error in `codex.stderr`.

**Base grants.** Codex runs `-s workspace-write` with `-c agents.enabled=false`. A writer gets its worktree, network for `git push`, the worktree's own gitdir plus the shared `objects`, `refs`, and `logs` (never the whole `.git`, which would also open `config` and `hooks`), and the parent directory of `$BEADS_DIR`. The parent is needed because bd's cross-process lock sits beside the store. A reviewer gets the bead store parent and no network, and its worktree stays read-only. The script refuses a main checkout, a repo with `extensions.worktreeConfig=true`, and any grant that would make the hooks dir or the shared `config` writable, because the coordinator later runs git outside the sandbox in that repo. A writer can move refs for any branch, not only its own. Every git command you run in a Codex worktree after the run carries `-c core.hooksPath=/dev/null -c core.fsmonitor=false`, which stops the worktree's own hooks and fsmonitor from running outside the sandbox. It does not cover a rewritten `.git` pointer file aimed at a Codex-made gitdir whose config sets `diff.external` or `core.pager`, so read the diff before trusting it.

**Extra grants.** Append `Grant: <abs path> [<abs path> ...]` to the spawn prompt, as its last sentence, and each path becomes one more `--add-dir`. Paths are absolute, exist, and hold no spaces. A file-path git remote needs its bare repo granted. A GitHub remote needs nothing extra.

1. Reach for Codex when the unit is one scoped implementation (`pstack:developer-codex`) or one review gate (`pstack:reviewer-codex`). Multi-kind work, tests, search, and orchestration stay on Claude. A plugin `PreToolUse` hook (`hooks/codex_exec_no_agents.py`) puts `shims/codex` first on `PATH` for any Bash command that mentions codex, and the shim adds `-c agents.enabled=false` when it runs `codex exec`. The hook never edits the command text. If Codex is already known unavailable this session, spawn plain `pstack:developer` or `pstack:reviewer` instead.
2. Create the bead and the worktree as poteto-mode's Agent runs paragraph says. Put the scope in the bead's description and the done-when in `--acceptance`; Codex reads them with `bd show`. The script picks the Codex model from `models.json`: the first `codex` entry of the `feature, refactoring` row for a writer, and of `judgment and prose` for a reviewer.
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

   Use the actor `developer-<id>` for a Codex writer, so a Claude fallback with the same prompt holds the same claim. Pin the watcher's model from the `codex watchers` row (its frontmatter carries `model: haiku`). The watcher returns nothing. Its completion notification means Codex exited.
4. Read the outcome from the bead and git, never from the watcher. The run dir is `${XDG_STATE_HOME:-~/.local/state}/pstack/codex-runs/<id>/<writer|reviewer>/`, with `codex.jsonl`, `codex.stderr`, `last-message.md`, and `refused.txt` when the script refused. Read `bd show <id> --json` and `bd comments <id>`.

   - Closed, with a close reason naming a SHA: done.
   - Open, `stage:built`, and a `ready at <SHA> on <branch>` comment: built.
   - A `verdict pass at <SHA>` or `verdict fail at <SHA>` comment: reviewed.
   - A `codex could not finish` comment: Codex did not finish.
   - Unclaimed, with `refused.txt` in the run dir: the script refused. Fix the cause it names, then spawn a fresh watcher.
   - Claimed with none of the above: read the last line of `codex.jsonl` and `codex.stderr`, then treat it as Codex did not finish.
5. Check the outcome against git before you trust it. Run `git -c core.hooksPath=/dev/null -c core.fsmonitor=false log <base>..<SHA>`, the same prefix on `git status --porcelain` in the worktree, and `git diff <base>..<SHA>`. For a built bead, `git ls-remote origin <branch>` must match the SHA. A SHA the bead claims counts only when git shows it.
6. When Codex did not finish, handle it in this order.

   - Record it on the bead. Write `codex did not finish: <reason>` to a `mktemp` file with the Write tool and add it as a comment (`bd comment <id> --file <path>`).
   - Tell the user in your next user-facing reply that Codex did not run for this task and why, even when the Claude fallback then succeeds. A spawner that is itself a subagent puts the failure in its own report instead.
   - Confirm no Codex run still holds the worktree: `pgrep -f "^bash <run dir>/run\.sh$"` finds nothing.
   - Spawn `pstack:developer` or `pstack:reviewer` without `isolation`, with the prompt the watcher got. A writer's claim succeeds again for the same actor, and the writer reads the bead and the worktree to continue from what Codex left.
7. Run the gates per the Gates section of [`references/beads-work-loop.md`](../references/beads-work-loop.md). After a writer run, spawn the reviewer. After a pass, spawn the tester. Check each result with the facts that section lists. Read the full diff yourself only when a check fails. The diff read in Base grants is a security check, and it always applies. Write your own summary.

**Reply:** your own summary of the change, the bead ID with its close reason or verdict, and the git evidence you checked them against.
