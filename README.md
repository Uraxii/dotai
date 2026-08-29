# dotai

Skills and agents for Claude Code, Codex, GitHub Copilot CLI, opencode, and
Hermes. One skills tree in the open Agent Skills format, shipped as a Claude
Code plugin and installable elsewhere through skills.sh. Layout follows pstack.

## Layout

| Dir       | What                                                    |
|-----------|---------------------------------------------------------|
| `skills/` | Every skill, `skills/<name>/SKILL.md`. Source of truth. |
| `agents/` | Named thin agents for graph readability, land in `~/.claude/agents`. |

## Install

Claude Code:

```
/plugin marketplace add Uraxii/dotai
/plugin install dotai@Uraxii
```

Codex: `/plugins`, add this repo as a marketplace (it carries
`.agents/plugins/marketplace.json`), install `dotai`.

Copilot CLI, Cursor, and the other targets skills.sh lists:

```
npx skills@latest add Uraxii/dotai
```

Hermes: `hermes skills tap add Uraxii/dotai`. opencode: clone the repo
and point `~/.config/opencode/skills` at `skills/`.

Then run `/setup-dotai` once: it offers the preamble lines for your global
instructions file and sets per-role models.

The named agents in `agents/` ship with the Claude Code plugin only; other
harnesses read `skills/` and do not use them.

Harness prefs (`CLAUDE.md`, `AGENTS.md`, `settings.json`, secrets) are not
tracked here.
