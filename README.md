# dotai

Skills and agents for Claude Code, Codex, GitHub Copilot CLI, opencode, and
Hermes. One skills tree in the open Agent Skills format, shipped as a Claude
Code plugin and installable elsewhere through skills.sh. Layout follows pstack.

## Layout

| Path      | What                                                    |
|-----------|---------------------------------------------------------|
| `skills/` | Every skill, `skills/<name>/SKILL.md`. Source of truth. |
| `agents/` | Named thin agents for graph readability, land in `~/.claude/agents`. |
| `themes/` | Editor themes. Source of truth only. Nothing installs them, so copy one into `~/.claude/themes/` yourself. |
| `statusline.sh` | Statusline command: usage bars and tokens per minute. Nothing installs it, so copy it to `~/.claude/statusline.sh` and set `statusLine` yourself. |
| `hooks/` | Hook scripts. `cap_bash_timeout.py` is a `PreToolUse` gate on long Bash timeouts; it is registered nowhere and does not run. Nothing installs them, so copy one into `~/.claude/hooks/` and wire it yourself. |

## Install

Claude Code:

```
/plugin marketplace add Uraxii/dotai
/plugin install dotai@Uraxii
```

Codex: `/plugins`, add this repo as a marketplace (it carries
`.agents/plugins/marketplace.json`), install `dotai`.

Copilot CLI:

```
copilot plugin marketplace add Uraxii/dotai
copilot plugin install dotai@Uraxii
```

Cursor and the other targets skills.sh lists:

```
npx skills@latest add Uraxii/dotai
```

Hermes: `hermes skills tap add Uraxii/dotai`. opencode: clone the repo
and point `~/.config/opencode/skills` at `skills/`.

Then run `/setup-dotai` once: it offers the preamble lines for your global
instructions file and sets per-role models.

The named agents in `agents/` ship with the Claude Code and Copilot CLI
plugin installs. skills.sh and opencode targets read `skills/` only.

Harness prefs (`CLAUDE.md`, `AGENTS.md`, `settings.json`, secrets) are not
tracked here.
