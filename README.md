# dotai

Skills, agents, and per-harness config for every AI harness on this machine:
Claude Code, Codex, GitHub Copilot CLI, opencode, Hermes. Layout follows
pstack: one skills tree in the open Agent Skills format, copied into each
harness by an agent-driven installer. LOCAL ONLY, no remote.

## Layout

| Dir                | What                                                        |
|--------------------|-------------------------------------------------------------|
| `skills/`          | Every skill, `skills/<name>/SKILL.md`. Source of truth.     |
| `agents/`          | Agent definitions (`zakia`, `subagent`, impeccable fleet).  |
| `harness/codex/`   | `AGENTS.md`, `rules/`, `schemas/` for `~/.codex`.           |
| `harness/copilot/` | instructions, refs, agents for `~/.copilot`.                |
| `harness/opencode/`| `agent/`, `command/`, `tui.json` for `~/.config/opencode`.  |
| `harness/hermes/`  | `SOUL.md`, profiles, skins, patches for `~/.hermes`.        |

## Install

Agent-driven: open any harness in this repo and invoke the `setup` skill. It
detects the harnesses present, asks which to target, dry-runs, then copies.

No agent yet (fresh machine):

```
bash skills/setup/scripts/install.sh --harness all --dry-run
bash skills/setup/scripts/install.sh --harness all --prune
```

Modes: `claude`, `codex`, `copilot`, `opencode`, `hermes`, `all`. Copies,
never symlinks. Each target root gets a `.dotai-manifest` listing what was
written; `--prune` removes files from an earlier install that the repo no
longer has and touches nothing else. Re-run after any edit here.

Where skills land: Claude `~/.claude/skills`; Codex `~/.agents/skills`;
Copilot `~/.copilot/skills`; opencode `~/.config/opencode/skills`; Hermes
`~/.hermes/skills`.

## Not in this repo, on purpose

- `~/.claude/settings.json`, `CLAUDE.md`, every `auth.json`, `.env`,
  `config.*`: user prefs and secrets, recreated by hand.
- `~/.claude/skills/krita` (14M) and `~/.codex/skills/.system`: vendor or
  live trees the harness manages.
- `skills/agent-workbench` is tracked here AND has its own upstream at
  `~/Projects/agent-workbench`; sync by hand.
- `~/.hermes` is 1.9G of runtime; the installer writes only the files listed
  in its manifest.
