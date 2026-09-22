# dotai

Skills and agents for Claude Code, Codex, GitHub Copilot CLI, opencode, and
Hermes, written in the open Agent Skills format. Eleven plugins live under
`plugins/`, and each one installs on its own. `pstack` carries the shared
machinery: the poteto-mode workflow, the principles, the playbooks, and the
agent files. The other ten each cover one tool or one job, and none of them
needs `pstack` installed.

## Plugins

<!-- dotai:plugins:start -->

| Plugin | What it does |
|---|---|
| `pstack` | Skills and thin named agents: poteto-mode, principles, playbooks, tools. |
| `artifact` | Explain a code change as a self-contained interactive HTML page. |
| `notion` | Reach Notion from the command line, and publish a code-change explainer as a Notion page. |
| `azure` | Read Azure DevOps projects, repos, pipelines, releases, and work items over the REST API. |
| `llm-wiki` | Keep research findings in a searchable project knowledgebase instead of re-deriving them. |
| `proton` | Read and store secrets in Proton Pass through pass-cli, so none lands in a repo or a shell history. |
| `sandbox` | Give an agent a throwaway podman container with its own clone of the repo, ports, and a virtual display. |
| `mpocock` | Compact a conversation into a handoff document another agent can pick the work up from. |
| `skills` | Review and author SKILL.md files, finding and repairing the smells that stop a skill triggering. |
| `bd` | Track, create, claim, and close repo issues with the bd (beads) tool, including dependency links. |
| `cbm` | Query the codebase-memory code graph from a shell: callers, dependencies, impact, dead code, and ADRs. |
| `steer` | Harness hooks that steer agent behaviour, independent of any skill. |

<!-- dotai:plugins:end -->

Every plugin keeps its skills in `plugins/<plugin>/skills/<name>/SKILL.md`.
No plugin cites a skill in another plugin, because a reader may have
installed only one of them. `scripts/validate-skills.py` fails a build that
breaks that rule.

## Layout

| Path      | What                                                    |
|-----------|---------------------------------------------------------|
| `plugins/<plugin>/skills/` | Every skill, `skills/<name>/SKILL.md`. Source of truth. |
| `plugins/pstack/models.json` | Model picks per role and harness. The only copy in the repository. The nine skills that spawn agents all ship in `pstack` and point at it by path. A per-harness override sheet in the user's config directory replaces a role for one harness without touching this repo (see the `setup-pstack` skill). |
| `plugins/pstack/agents/` | Claude and Copilot agent files. |
| `scripts/` | CI checks: `validate-models.py` checks `models.json` only names models it can back, `validate-skills.py` checks skill links, cross-plugin citations, and frontmatter, and `generate-plugin-manifests.py` writes all 33 plugin manifests, both marketplace files, and the plugin table above from one list. Tests in `scripts/tests/`. |
| `themes/` | Editor themes. Source of truth only. Nothing installs them, so copy one into `~/.claude/themes/` yourself. |
| `output-styles/` | Output styles, `output-styles/<name>.md`. Nothing installs them, so copy one into `~/.claude/output-styles/` and select it with `/output-style` yourself. |
| `statusline.sh` | Statusline command: usage bars and tokens per minute. Nothing installs it, so copy it to `~/.claude/statusline.sh` and set `statusLine` yourself. |
| `plugins/pstack/hooks/` | Hook scripts tied to pstack skills and playbooks. `handoff-token-flag.py` warns before context compaction; plugin installation wires it for Claude Code, Codex, and Copilot CLI. `session_start_context.py` reminds the agent to load `poteto-mode` at session start; plugin installation wires it for Claude Code, Codex, and Copilot CLI. `codex_watcher_guard.py` gates commands from the `delegate-to-codex` playbook. `opencode-reminder-plugin.ts` (in the same directory) wires the session-start reminder into opencode. Wiring it into Hermes by hand is not covered by any skill here. See [Session-start reminder](#session-start-reminder) below for what each harness can and cannot do. Add `.nikki-agents/` to the exclude config of your editor, LSP, and any semantic index: `.git/info/exclude` covers git, ripgrep, and fd, but an indexer that keeps its own ignore list walks the worktrees and ends up crawling six figures of files in a repo with a few hundred tracked ones. |
| `plugins/steer/hooks/` | `opus_5_reduce_output.py` is a Claude Code `Stop` hook that asks for a plain-English recap at the end of every turn on Opus 5 and Fable 5; it gates on the model alone, because this user delegates edits to subagents where a turn-window edit count sees nothing. Plugin installation wires it, and no other harness gets it. |

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
`plugins/<plugin>/skills/`. For the session-start reminder, also symlink
`plugins/pstack/hooks/opencode-reminder-plugin.ts` into
`~/.config/opencode/plugin/` (a copy breaks the plugin's lookup of its
sibling script, so symlink it).

Claude Code and Copilot CLI read the agent files in `plugins/pstack/agents/`
from the `pstack` plugin. opencode and Hermes use their native delegation
with dotai roles carried in scoped briefs. This repo no longer ships Codex
agent files, so a spawner on Codex reads the role preferences in
`plugins/pstack/models.json` instead. The skills.sh and opencode targets read
`plugins/<plugin>/skills/` only.

`plugins/pstack/models.json` is the only copy of the model picks. No skill
repeats it. The nine skills that spawn agents all ship in `pstack`, and each
points at the file by path and tells the reader to resolve it two directories
up from the skill's own directory, so a spawner working outside this repo
still finds it. A per-harness override sheet in the user's own config
directory can replace a role for one harness without touching this repo (see
the `setup-pstack` skill). After changing `models.json`, check that it only
names models it can back, then check every plugin for broken links, citations
that cross a plugin boundary, and malformed skill frontmatter:

```
python3 scripts/validate-models.py
python3 scripts/validate-skills.py plugins/*/skills
```

After changing the plugin list in `scripts/generate-plugin-manifests.py`,
rerun it and commit what it writes:

```
python3 scripts/generate-plugin-manifests.py
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
(`website/docs/user-guide/features/hooks.md:1871`). Adding the hook by hand
is not covered by any skill here.
