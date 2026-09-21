---
name: reviewer-codex
description: "Default for one review gate on Claude Code: starts a read-only Codex run, replies with five lines pointing at the repo it read."
color: gray
tools: Bash, Write
---

### Delegate to Codex

**In plain words:** hand one coding or review job to Codex, a different AI tool, instead of doing it here. A small watcher agent starts the Codex run and tells you where it landed; you read the result yourself and check it against git.

**You own the run.** Claude Code only; skip this playbook on any other harness. The watcher carries its own steps in `plugins/pstack/agents/developer-codex.md` and `plugins/pstack/agents/reviewer-codex.md`, and `hooks/codex_watcher_guard.py` locks it to exactly those commands. This page is the owner's half.

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
   poteto-mode: /absolute/path/of/poteto-mode/SKILL.md
   ```

   `kind` is `writer` or `reviewer`. `worktree` is `create` or an existing absolute path, and a reviewer omits it. Take `model` from `plugins/pstack/models.json`: the first `codex` entry of the `feature, refactoring` row for a writer, of `judgment and prose` for a reviewer.
4. Spawn the watcher without `isolation`. Its worktree comes from the header, not from Claude's own worktree placement. Pin the watcher's own model from the `codex watchers` row.
5. Read the reply. It is five lines and nothing else: `fallback`, `command`, `exit code`, `worktree`, `base`. The watcher never opens the report and never retypes Codex's output, so those five lines are all you get from it.
6. `fallback: none`: open `<repo>/.nikki-agents/codex-runs/<name>/report.md` yourself, then run `git log` and `git diff <base>..HEAD` in the reply's `worktree`. A commit the report claims counts only when git shows it. No report file at that path despite `fallback: none` means the run failed anyway; treat it as step 7.
7. `fallback: claude`: spawn `pstack:developer` or `pstack:reviewer` with the same brief. A writer fallback works in the named `worktree` when that line is not `(none)` and reads git state there first; a partial `report.md` at the run path is worth reading. When `exit code: timeout` sent you here, run `pgrep -af "codex exec"` and confirm no run still holds that worktree before the fallback writer touches it.
8. Review the diff yourself and write your own summary. Codex's report is evidence, not your verdict.

**Reply:** your own summary of the diff, the run's report path, and the git evidence you checked the report against.
