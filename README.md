# dotai

Skills and agents for Claude Code, Codex, GitHub Copilot CLI, opencode, and
Hermes. One skills tree in the open Agent Skills format, copied into each
harness by an agent-driven installer. Layout follows pstack.

## Layout

| Dir       | What                                                    |
|-----------|---------------------------------------------------------|
| `skills/` | Every skill, `skills/<name>/SKILL.md`. Source of truth. |
| `agents/` | Named thin agents for graph readability, land in `~/.claude/agents`. |

## Install

Open a harness inside this repo and invoke `raxii-dotai-setup`. It detects
the harnesses present, asks which to target, dry-runs, then copies.

Without an agent:

```
bash skills/raxii-dotai-setup/scripts/install.sh --harness all --prune
```

Modes: `claude`, `codex`, `copilot`, `opencode`, `hermes`, `all`. Add
`--dry-run` to preview. Copies only, never symlinks. Each target root gets a
`.dotai-manifest`; `--prune` removes files from an earlier install that the
repo no longer has and touches nothing else. Re-run after any edit.

Skills land in `~/.claude/skills`, `~/.agents/skills` (Codex),
`~/.copilot/skills`, `~/.config/opencode/skills`, `~/.hermes/skills`.

Harness prefs (`CLAUDE.md`, `AGENTS.md`, `settings.json`, secrets) are not
tracked here.
