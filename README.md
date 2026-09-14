# dotai

Skills and agents for Claude Code, Codex, GitHub Copilot CLI, opencode, and
Hermes. One skills tree in the open Agent Skills format, shipped as the
`pstack-nikki` plugin and installable elsewhere through skills.sh. Layout
follows pstack: the plugin lives under `plugins/pstack-nikki/`, the same
place pstack-claude keeps `plugins/pstack/`.

## Layout

| Path      | What                                                    |
|-----------|---------------------------------------------------------|
| `plugins/pstack-nikki/skills/` | Every skill, `skills/<name>/SKILL.md`. Source of truth. |
| `plugins/pstack-nikki/models.json` | Model picks per role. Source of truth; stamped into skills. |
| `plugins/pstack-nikki/agents/` | Generated Claude and Copilot agent files. |
| `plugins/pstack-nikki/skills/setup-dotai/references/` | Platform-neutral agent definitions. |
| `plugins/pstack-nikki/skills/setup-dotai/assets/codex-agents/` | Generated Codex agent files. |
| `plugins/pstack-nikki/skills/setup-dotai/scripts/` | Generates and installs agent files. |
| `themes/` | Editor themes. Source of truth only. Nothing installs them, so copy one into `~/.claude/themes/` yourself. |
| `output-styles/` | Output styles, `output-styles/<name>.md`. Nothing installs them, so copy one into `~/.claude/output-styles/` and select it with `/output-style` yourself. |
| `statusline.sh` | Statusline command: usage bars and tokens per minute. Nothing installs it, so copy it to `~/.claude/statusline.sh` and set `statusLine` yourself. |
| `plugins/pstack-nikki/hooks/` | Hook scripts. `cap_bash_timeout.py` is a `PreToolUse` gate on long Bash timeouts; it is registered nowhere and does not run. `handoff-token-flag.py` warns before context compaction; plugin installation wires it for Claude Code, Codex, and Copilot CLI. Add `.nikki-agents/` to the exclude config of your editor, LSP, and any semantic index: `.git/info/exclude` covers git, ripgrep, and fd, but an indexer that keeps its own ignore list walks the worktrees and ends up crawling six figures of files in a repo with a few hundred tracked ones. |

## Install

Claude Code:

```
/plugin marketplace add Uraxii/dotai
/plugin install pstack-nikki@Uraxii
```

Codex CLI:

```
codex plugin marketplace add Uraxii/dotai --ref main
codex plugin add pstack-nikki@uraxii
```

In the Codex app, open `/plugins`, add `Uraxii/dotai` as a marketplace,
then install `pstack-nikki`.

Copilot CLI:

```
copilot plugin marketplace add Uraxii/dotai
copilot plugin install pstack-nikki@Uraxii
```

Cursor and the other targets skills.sh lists:

```
npx skills@latest add Uraxii/dotai/plugins/pstack-nikki
```

Hermes: `hermes skills tap add Uraxii/dotai/plugins/pstack-nikki`. opencode:
clone the repo and point `~/.config/opencode/skills` at
`plugins/pstack-nikki/skills/`.

Then run `/setup-dotai` once: it offers the preamble lines for your global
instructions file, installs named agents where needed, and sets per-role
models.

Claude Code and Copilot CLI read the generated files in
`plugins/pstack-nikki/agents/` from the plugin. Codex needs its generated
files copied into its user config directory; `setup-dotai` handles that.
OpenCode and Hermes use their native delegation with dotai roles carried in
scoped briefs. Codex agent files omit `model` and `model_reasoning_effort`,
so the role preferences in `plugins/pstack-nikki/models.json`
remain authoritative at spawn time. skills.sh and opencode targets read
`plugins/pstack-nikki/skills/` only.

After changing an agent definition under
`plugins/pstack-nikki/skills/setup-dotai/references/`, regenerate and check
the platform files:

```
python3 plugins/pstack-nikki/skills/setup-dotai/scripts/generate-agent-configs.py
python3 plugins/pstack-nikki/skills/setup-dotai/scripts/generate-agent-configs.py --check
```

After changing `plugins/pstack-nikki/models.json`, stamp its picks into the
skills that name a role from it, then check the tree for broken links and
malformed skill frontmatter:

```
python3 plugins/pstack-nikki/skills/setup-dotai/scripts/generate-models.py
python3 plugins/pstack-nikki/skills/setup-dotai/scripts/validate-skills.py plugins/pstack-nikki/skills
```

Harness prefs (`CLAUDE.md`, `AGENTS.md`, `settings.json`, secrets) are not
tracked here.
