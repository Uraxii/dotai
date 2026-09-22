### Delegate to Codex

**In plain words:** hand one coding or review job to Codex, a different AI tool, instead of doing it here. A small watcher agent starts the Codex run and tells you where it landed; you read the result yourself and check it against git.

**You own the run.** Claude Code only; skip this playbook on any other harness. The watcher's own steps are `references/codex-watcher-body.md`, which is the whole body of both watchers, and `hooks/codex_watcher_guard.py` locks it to exactly those commands. This page is the owner's half. The watcher prefers `codex-agent`, a dedicated Codex install with its own `CODEX_HOME`, so a run using it never shares the user's interactive Codex session, config, or authentication state.

No installer creates `codex-agent`; create it yourself, once per machine, to get that isolation:

```sh
#!/bin/sh
export CODEX_HOME="$HOME/.codex-agent"
exec "$(command -v codex)" "$@"
```

Without it on `PATH`, the watcher falls back to bare `codex`, sharing your interactive Codex session, config, and authentication state instead of isolating them. Delegation still runs; it just loses the isolation the wrapper buys.

1. Reach for Codex when the unit is one scoped implementation (`pstack:developer-codex`) or one review gate (`pstack:reviewer-codex`). Multi-kind work, tests, search, and orchestration stay on Claude: the watcher holds only Bash and Write, and the run starts with `-c agents.enabled=false`, so Codex does the brief itself and spawns no helpers. Codex already known unavailable this session: spawn plain `pstack:developer` or `pstack:reviewer` instead.
2. Pick a run `name` fresh for this repo, lowercase letters, digits, and dashes. A reused name either fails the watcher's `git worktree add` step or leaves the previous run's `report.md` for you to misread as this one's.
3. Open the watcher's prompt with this header, then the brief:

   ```
   CODEX RUN
   kind: writer
   repo: /absolute/path/of/the/main/checkout
   name: short-slug
   model: gpt-5.6-terra
   worktree: create
   base: develop
   poteto-mode: /absolute/path/of/poteto-mode/SKILL.md
   ```

   `kind` is `writer` or `reviewer`. `worktree` is `create` or the absolute path of an existing worktree, and a reviewer omits it. An existing worktree must be exactly `<repo>/.nikki-agents/worktrees/<x>` or `<repo>/.claude/worktrees/<x>`, with `<x>` one path segment other than `.git`. A writer commits only on an `agent/` branch, so an existing worktree on any other branch cannot commit. `base` is the commit-ish the new worktree starts from (a branch, tag, or SHA that exists in `repo`), required when `worktree: create` and omitted otherwise. Put the branch you actually want the writer working from, such as `develop` or `agent/pr2-split`: the watcher's own checkout can sit on any branch, and it takes `base` literally instead of inheriting that branch. `hooks/codex_watcher_guard.py` never reads this header. It checks only that the watcher's command hangs together: under `workspace-write`, `-C` is the directory Codex may write to, and the guard requires it to take one of those two shapes, built on the same tree that receives the report. Any other `worktree`, including one nested deeper, therefore fails the guard. A command naming some other tree in every one of its paths is self-consistent and passes, so `repo` is yours to get right. Take `model` from the plugin's `models.json`, two directories up from the `poteto-mode` skill's own directory and `plugins/pstack/models.json` in the repo (see that skill's Models section): the first `codex` entry of the `feature, refactoring` row for a writer, of `judgment and prose` for a reviewer.
4. Spawn the watcher without `isolation`, always. Its worktree comes from the header, not from Claude's own worktree placement. Under `isolation: "worktree"` the harness auto-cleans a worktree that git reports as unchanged. The watcher's only write is a prompt file under the gitignored `.nikki-agents/`, so git reports the worktree unchanged, and the harness deletes it along with the Codex worktree nested under it while `codex exec` is still writing there. Pin the watcher's own model from the `codex watchers` row.
5. Read the reply. It is five lines and nothing else: `fallback`, `command`, `exit code`, `worktree`, `base`. The watcher never opens the report and never retypes Codex's output, so those five lines are all you get from it. `exit code` is a number, `timeout`, `denied`, or `(none)`.
6. `fallback: none`: open `<repo>/.nikki-agents/codex-runs/<name>/report.md` yourself, then run `git log` and `git diff <base>..HEAD` in the reply's `worktree`. A writer commits its own work there, so expect commits rather than an uncommitted tree. Its `workspace-write` sandbox grants the worktree itself, which is where it edits source files, plus the four paths a commit writes under the shared git directory: `<repo>/.git/objects`, `<repo>/.git/refs/heads/agent`, `<repo>/.git/logs/refs/heads/agent`, and `<repo>/.git/worktrees/<basename of the worktree>`. Nothing else under `.git` is writable, so `.git/hooks` and `.git/config` stay read-only and a run cannot plant a hook that later executes on your machine. The two narrow ref grants mean a writer commits only to a branch under `agent/`, which is what the watcher creates. Hand a writer an existing worktree on a branch outside `agent/` and it cannot commit, which is a deliberate limit. The grants protect `main`, `develop`, and other branches outside `agent/`, but not one agent's branch from another. Every writer can write every `agent/` branch and its reflog, so a hostile run could move or delete another agent's branch. Run those two git commands anyway, because a commit the report claims counts only when git shows it. No report file at that path despite `fallback: none` means the run failed anyway; treat it as step 7.
7. `fallback: claude`: read `exit code` before you spawn anything.

   - `denied`. The guard blocked the `command` line, or, when `command` is `(none)`, the watcher refused a header the guard would have blocked. Spawn no fallback writer yet. Compare the header you wrote in step 3 against the reply. The usual cause is a `worktree` path that is not one segment below `<repo>/.nikki-agents/worktrees` or `<repo>/.claude/worktrees`, or a run `name` that is not a slug. Fix the header, then spawn a fresh watcher with a fresh `name`. Spawn a Claude fallback only when the header was already right, and give it a worktree you pick inside `repo`. Never point a fallback writer at a path outside `repo`: no hook guards a Claude writer. A right header that the guard still blocks means the guard and this playbook disagree, which is a bug in one of them.
   - Anything else. Spawn `pstack:developer` or `pstack:reviewer` with the same brief. A writer fallback works in the named `worktree` when that line is not `(none)` and reads git state there first; a partial `report.md` at the run path is worth reading. When `exit code: timeout` sent you here, confirm no run still holds that worktree before the fallback writer touches it. A plain `pgrep -af "codex exec"` fails two ways: it can self-match an ancestor process whose own command line carries that text, and it false-positives on any unrelated process that does too. Key the check to `<worktree>` instead, since `-C <worktree>` survives verbatim into the live process's argv once `codex-agent` execs the codex binary: `pgrep -af -- "codex exec.*-C <worktree>( |$)"`. Nothing found means no run still holds it.
8. Review the diff yourself and write your own summary. Codex's report is evidence, not your verdict.

**Reply:** your own summary of the diff, the run's report path, and the git evidence you checked the report against.
