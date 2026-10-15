# dotai

Skills and agents for Claude Code, Codex, GitHub Copilot CLI, opencode, and
Hermes, written in the open Agent Skills format. Fifteen plugins live under
`plugins/`, and each one installs on its own. `pstack` carries the shared
machinery: the poteto-mode workflow, the principles, the playbooks, and the
agent files. The other fourteen each cover one tool or one job. Only
`codex-worker` refers to `pstack` skills, so install it next to `pstack`.

## Plugins

<!-- dotai:plugins:start -->

| Plugin | What it does |
|---|---|
| `pstack` | If you want to go fast, go deep first. pstack helps you write less, but higher quality code. rigorous agent workflows you can parallelize with confidence. Ported from cursor/plugins/pstack to Claude Code. Original pstack by Lauren Tan (poteto). |
| `artifact` | Explain a code change as a self-contained interactive HTML page. |
| `notion` | Reach Notion from the command line, and publish a code-change explainer as a Notion page. |
| `azure` | Read Azure DevOps projects, repos, pipelines, releases, and work items over the REST API. |
| `llm-wiki` | Keep research findings in a searchable project knowledgebase instead of re-deriving them. |
| `proton` | Read and store secrets in Proton Pass through pass-cli, so none lands in a repo or a shell history. |
| `sandbox` | Give an agent a throwaway podman container with its own clone of the repo, ports, and a virtual display. |
| `codex-worker` | Delegate a code change from Claude Code to an outside Codex CLI worker. |
| `mpocock` | Compact a conversation into a handoff document another agent can pick the work up from. |
| `skills` | Review and author SKILL.md files, finding and repairing the smells that stop a skill triggering. |
| `codebase-memory` | Query a code graph through the codebase-memory-mcp server, skill, and graph-verification agents. |
| `caveman` | Answer in a compressed register that drops filler and keeps every technical fact. |
| `steer` | Harness hooks that steer agent behaviour, independent of any skill. |
| `shunt` | Shunts large reads to small subagents and boilerplate generation to Portal AiKA to save main-agent context tokens. |
| `personal-instructions` | Inject a hand-edited instructions.md at session start and, where the harness has a subagent-start hook, subagent start. |

<!-- dotai:plugins:end -->

Every plugin keeps its skills in `plugins/<plugin>/skills/<name>/SKILL.md`.
No plugin cites a skill in another plugin, because a reader may have
installed only one of them.

## Layout

| Path      | What                                                    |
|-----------|---------------------------------------------------------|
| `plugins/<plugin>/skills/` | Every skill, `skills/<name>/SKILL.md`. Source of truth. |
| `plugins/pstack/models.json` | Model picks per role and harness. The only copy in the repository. Every skill that picks a model by role ships in `pstack` and points at it by path. A per-harness override sheet in the user's config directory replaces a role for one harness without touching this repo (see the `setup-pstack` skill). |
| `plugins/pstack/agents/` | Claude and Copilot agent files. |
| `scripts/` | `generate-plugin-manifests.py` writes all 33 plugin manifests, both marketplace files, and the plugin table above from one list. |
| `themes/` | Editor themes. Source of truth only. Nothing installs them, so copy one into `~/.claude/themes/` yourself. |
| `output-styles/` | Output styles, `output-styles/<name>.md`. Nothing installs them, so copy one into `~/.claude/output-styles/` and select it with `/output-style` yourself. |
| `statusline.sh` | Statusline command: usage bars and tokens per minute. Nothing installs it, so copy it to `~/.claude/statusline.sh` and set `statusLine` yourself. |
| `plugins/mpocock/hooks/` | `handoff-token-flag.py` warns before context compaction and points the agent at the `handoff` skill, which ships in this same plugin. Plugin installation wires it for Claude Code and Codex. |
| `plugins/pstack/hooks/` | `session-start.sh` injects the poteto-mode routing mandate at session start, wired by `hooks.json` (Claude Code), `codex-hooks.json` (Codex), and `copilot-hooks.json` (Copilot CLI, which also gets `pre-tool-use.sh`). A `session hook: off` line in the user's `pstack-models.md` sheet turns it off. See [Session-start reminder](#session-start-reminder). Add `.nikki-agents/` to the exclude config of your editor, LSP, and any semantic index: `.git/info/exclude` covers git, ripgrep, and fd, but an indexer that keeps its own ignore list walks the worktrees and ends up crawling six figures of files in a repo with a few hundred tracked ones. |
| `plugins/steer/hooks/` | `opus_5_reduce_output.py` is a Claude Code `Stop` hook that asks for a plain-English recap at the end of a turn on Opus 5 or Fable 5 that changed something. A turn that mutated nothing has nothing to recap, so it ends silently. Spawning a subagent counts as a mutation, because a delegate's own edits never reach this transcript. Plugin installation wires it, and no other harness gets it. |

## Install

Every plugin installs the same way. Replace `<plugin>` with a name from the
table above.

Claude Code:

```
/plugin marketplace add Uraxii/dotai
/plugin install <plugin>@Uraxii
```

Codex CLI:

```
codex plugin marketplace add Uraxii/dotai --ref main
codex plugin add <plugin>@uraxii
```

In the Codex app, open `/plugins`, add `Uraxii/dotai` as a marketplace, then
install the plugins you want.

Copilot CLI:

```
copilot plugin marketplace add Uraxii/dotai
copilot plugin install <plugin>@Uraxii
```

Cursor and the other targets skills.sh lists:

```
npx skills@latest add Uraxii/dotai/plugins/<plugin>
```

Hermes: `hermes skills tap add Uraxii/dotai/plugins/<plugin>`.

opencode: clone the repo and point `~/.config/opencode/skills` at
`plugins/<plugin>/skills/`.

Claude Code and Copilot CLI read the agent files in `plugins/pstack/agents/`
from the `pstack` plugin. opencode and Hermes use their native delegation
with dotai roles carried in scoped briefs. This repo no longer ships Codex
agent files, so a spawner on Codex reads the role preferences in
`plugins/pstack/models.json` instead. The skills.sh and opencode targets read
`plugins/<plugin>/skills/` only.

`plugins/pstack/models.json` is the only copy of the model picks. No skill
repeats it. Every skill that picks a model by role ships in `pstack`, and
each one points at the file by path and tells the reader to resolve it two
directories up from the skill's own directory, so a spawner working outside
this repo still finds it. A per-harness override sheet in the user's own config
directory can replace a role for one harness without touching this repo (see
the `setup-pstack` skill).

After changing the plugin list in `scripts/generate-plugin-manifests.py`,
rerun it and commit what it writes:

```
python3 scripts/generate-plugin-manifests.py
```

Harness prefs (`CLAUDE.md`, `AGENTS.md`, `settings.json`, secrets) are not
tracked here.

## Session-start reminder

The `pstack` plugin injects the "load `poteto-mode`" mandate at session start through `plugins/pstack/hooks/session-start.sh`. Each harness has its own hooks file, and each passes its name to the script.

| Harness | Hooks file | Event |
|---|---|---|
| Claude Code | `plugins/pstack/hooks/hooks.json` | `SessionStart` (`startup\|resume\|clear\|compact`) |
| Codex | `plugins/pstack/hooks/codex-hooks.json` | `SessionStart` (same matcher; Windows runs `session-start.ps1`) |
| Copilot CLI | `plugins/pstack/hooks/copilot-hooks.json` | `sessionStart` (same matcher), plus a `PreToolUse` hook, `pre-tool-use.sh` |
| Pi | `plugins/pstack/pi/` (extension) | Adds the mandate to the system prompt at every agent start |

Plugin installation wires the hooks. Codex asks the user to trust plugin hooks through `/hooks` first. Setting `session hook: off` in the harness's `pstack-models.md` sheet (see `setup-pstack`) stops injection on every harness above.

opencode, Hermes, Gemini CLI, and the other skills.sh targets read the skills only. They get no session-start reminder from this repo, so load `poteto-mode` by hand there.
