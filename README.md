# dotai

Skills and agents for Claude Code, Codex, GitHub Copilot CLI, opencode, and
Hermes. One skills tree in the open Agent Skills format, shipped as the
`pstack` plugin and installable elsewhere through skills.sh. The plugin
lives under `plugins/pstack/`, the same place pstack-claude keeps its own.

## Layout

| Path      | What                                                    |
|-----------|---------------------------------------------------------|
| `plugins/pstack/skills/` | Every skill, `skills/<name>/SKILL.md`. Source of truth. |
| `plugins/pstack/models.json` | Model picks per role and harness. The only copy; skills point at it by path, and a per-harness override sheet in the user's config directory replaces a role for one harness without touching this repo (see the `setup-pstack` skill). |
| `plugins/pstack/agents/` | Generated Claude and Copilot agent files. |
| `plugins/pstack/skills/setup-dotai/references/` | Platform-neutral agent definitions. |
| `plugins/pstack/skills/setup-dotai/assets/codex-agents/` | Generated Codex agent files. |
| `plugins/pstack/skills/setup-dotai/scripts/` | Generates and installs agent files. |
| `themes/` | Editor themes. Source of truth only. Nothing installs them, so copy one into `~/.claude/themes/` yourself. |
| `output-styles/` | Output styles, `output-styles/<name>.md`. Nothing installs them, so copy one into `~/.claude/output-styles/` and select it with `/output-style` yourself. |
| `statusline.sh` | Statusline command: usage bars and tokens per minute. Nothing installs it, so copy it to `~/.claude/statusline.sh` and set `statusLine` yourself. |
| `plugins/pstack/hooks/` | Hook scripts. `cap_bash_timeout.py` is a `PreToolUse` gate on long Bash timeouts; it is registered nowhere and does not run. `handoff-token-flag.py` warns before context compaction; plugin installation wires it for Claude Code, Codex, and Copilot CLI. `recap_on_stop.py` is a Claude Code `Stop` hook that asks for a plain-English recap at the end of every turn on Opus 5 and Fable 5; it gates on the model alone, because this user delegates edits to subagents where a turn-window edit count sees nothing. Plugin installation wires it, and no other harness gets it. `session_start_context.py` reminds the agent to load `poteto-mode` at session start; plugin installation wires it for Claude Code, Codex, and Copilot CLI, `opencode-reminder-plugin.ts` (same directory) wires it into opencode, and the `setup-dotai` skill walks through wiring it into Hermes by hand. See [Session-start reminder](#session-start-reminder) below for what each harness can and cannot do. Add `.nikki-agents/` to the exclude config of your editor, LSP, and any semantic index: `.git/info/exclude` covers git, ripgrep, and fd, but an indexer that keeps its own ignore list walks the worktrees and ends up crawling six figures of files in a repo with a few hundred tracked ones. |

## Install

Claude Code:

```
/plugin marketplace add Uraxii/dotai
/plugin install pstack@Uraxii
```

Codex CLI:

```
codex plugin marketplace add Uraxii/dotai --ref main
codex plugin add pstack@uraxii
```

In the Codex app, open `/plugins`, add `Uraxii/dotai` as a marketplace,
then install `pstack`.

Copilot CLI:

```
copilot plugin marketplace add Uraxii/dotai
copilot plugin install pstack@Uraxii
```

Cursor and the other targets skills.sh lists:

```
npx skills@latest add Uraxii/dotai/plugins/pstack
```

Hermes: `hermes skills tap add Uraxii/dotai/plugins/pstack`. opencode:
clone the repo, point `~/.config/opencode/skills` at
`plugins/pstack/skills/`, and symlink
`plugins/pstack/hooks/opencode-reminder-plugin.ts` into
`~/.config/opencode/plugin/` for the session-start reminder (a copy breaks
the plugin's lookup of its sibling script, so symlink it).

Then run `/setup-dotai` once: it offers the preamble lines for your global
instructions file, installs named agents where needed, and sets per-role
models.

Claude Code and Copilot CLI read the generated files in
`plugins/pstack/agents/` from the plugin. Codex needs its generated
files copied into its user config directory; `setup-dotai` handles that.
OpenCode and Hermes use their native delegation with dotai roles carried in
scoped briefs. Codex agent files omit `model` and `model_reasoning_effort`,
so the role preferences in `plugins/pstack/models.json`
remain authoritative at spawn time. skills.sh and opencode targets read
`plugins/pstack/skills/` only.

After changing an agent definition under
`plugins/pstack/skills/setup-dotai/references/`, regenerate and check
the platform files:

```
python3 plugins/pstack/skills/setup-dotai/scripts/generate-agent-configs.py
python3 plugins/pstack/skills/setup-dotai/scripts/generate-agent-configs.py --check
```

`plugins/pstack/models.json` is the only copy of the model picks. No skill
repeats it; each points at the file by path, and a per-harness override sheet
in the user's own config directory can replace a role for one harness without
touching this repo (see the `setup-pstack` skill). After changing
`models.json`, check that it only names models it can back, then check the
tree for broken links and malformed skill frontmatter:

```
python3 plugins/pstack/skills/setup-dotai/scripts/validate-models.py
python3 plugins/pstack/skills/setup-dotai/scripts/validate-skills.py plugins/pstack/skills
```

Harness prefs (`CLAUDE.md`, `AGENTS.md`, `settings.json`, secrets) are not
tracked here.

## Session-start reminder

Every harness gets the same "load `poteto-mode`" nudge from
`plugins/pstack/hooks/session_start_context.py`, through each harness's
own hook system. Only Claude Code and Codex have been run live; the rest are
**LIVE-UNVERIFIED**, proven by unit tests against the payload and output
shapes their own docs or source describe, not by a real session (this dev
machine cannot install Copilot CLI, opencode, or Hermes).

| Harness | Event | Fires | Injects into | Source |
|---|---|---|---|---|
| Claude Code | `SessionStart` (`startup\|clear\|compact`) | Once, at each named point | Context, automatically | Claude Code hooks docs |
| Codex | `SessionStart`, `PostCompact` | Once each | Context, via `hookSpecificOutput.additionalContext` | Codex hooks docs |
| Copilot CLI | `sessionStart` | Once per job, new session only (not on resume) | Context, via `additionalContext` | docs.github.com Copilot CLI hooks reference, "Hook events" and "Hook event input payloads" / `sessionStart`; changelog 1.0.11 and 1.0.22; fetched 2026-09-14 |
| opencode | none that fires once at session start and can inject; `experimental.chat.system.transform` runs before every LLM request instead | Every request | System prompt array | `anomalyco/opencode@228e9095`, `packages/plugin/src/index.ts:291-296`, `packages/opencode/src/plugin/index.ts:259`; cloned 2026-09-14 |
| Hermes | `pre_llm_call`, gated on `extra.is_first_turn` | Once per session (script-side gate; the event itself fires every turn) | That turn's user message, via `{"context": ...}` | `NousResearch/hermes-agent@498abb6`, `website/docs/user-guide/features/hooks.md:458,677-696`, `agent/turn_context.py:663-690`; cloned 2026-09-14 |

Copilot CLI's `sessionStart` `additionalContext` shipped in 1.0.11
(2026-03-23) after being silently dropped
([github/copilot-cli#2142](https://github.com/github/copilot-cli/issues/2142)).
A later report
([github/copilot-cli#4665](https://github.com/github/copilot-cli/issues/4665))
says the CLI re-injects the same `additionalContext` on every turn instead of
once, closed 2026-09-02 with no changelog line confirming the fix; that
replay happens inside Copilot CLI, not from repeated hook invocations, so no
guard on this script's side can prevent it. The documented fallback,
`userPromptSubmitted`'s `modifiedPrompt`, is explicitly dropped for command
hooks (hooks-reference.md line 342: "Command and HTTP config-file
`userPromptSubmitted` hooks have their output dropped"), so `handoff-token-flag.py`'s
docstring claim that Copilot's prompt hook cannot inject context still holds;
this script does not implement that fallback.

opencode has no per-session hook at all, so `opencode-reminder-plugin.ts`
uses the one hook that can inject text and pushes the reminder onto the
system prompt before every LLM request rather than once at start; a plugin
can dedupe by `sessionID` if that granularity ever matters more than the
extra array entry does.

Hermes hooks require the user's consent on first use, recorded in
`~/.hermes/shell-hooks-allowlist.json`
(`website/docs/user-guide/features/hooks.md:1871`); `setup-dotai`'s Hermes
section walks through adding the hook.
