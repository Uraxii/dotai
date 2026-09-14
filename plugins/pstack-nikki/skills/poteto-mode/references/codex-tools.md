# Codex tool mapping

pstack-nikki skills are written in Claude Code tool language: the `Agent`
tool, `isolation: "worktree"`, `SendMessage`, `AskUserQuestion`, the todolist
(`TodoWrite`), the `Skill` tool, `Read`/`Write`/`Edit`/`Bash`,
`WebFetch`/`WebSearch`, and Claude model slugs. Read this when a skill names
one of those on Codex. The skill file itself does not change; only the tool
you call to follow it does.

Verified against Codex CLI 0.154.0 (`codex --version`) on 2026-09-14: `codex
--help`, `codex features list`, and the `openai/codex` source at commit
`b876f889818e99b371e3078e3f499d75164c13bb` (`codex-rs/`, cloned shallow for
this check). File:line citations below point into that tree. Docs:
learn.chatgpt.com/docs/hooks for the hook side; no public reference for the
tool schemas, so the source is primary.

## Tool actions

| Claude Code action | Codex equivalent | Source |
|---|---|---|
| Read a file | `shell` tool | No dedicated read tool; `shell_spec.rs:67` names it `"shell"`. |
| Create / edit / delete a file | `apply_patch` | `handlers/apply_patch_spec.rs:19`, `handlers/apply_patch.rs:343`. |
| Run a shell command | `shell` | `shell_spec.rs:67`. |
| Search file contents / find files | `shell` (`rg`, `grep`, `find`) | No dedicated search tool; the `search_tool` feature is `removed` (`codex features list`). |
| Fetch a URL | `shell` with `curl`/`wget` | No dedicated fetch tool. |
| Search the web | `web_search` | `tools/src/tool_spec.rs:39` (`ToolSpec::WebSearch`). |
| Invoke a skill (`Skill` tool, `/command`) | Skills load natively; follow the instructions | `codex features list`: `plugins stable true`, `plugin_sharing stable true`. |
| Track tasks (`TodoWrite`, the todolist) | `update_plan` | `handlers/plan_spec.rs:43`, `handlers/plan.rs:50`. |
| Ask a fixed-choice question (`AskUserQuestion`) | `request_user_input` | `handlers/request_user_input_spec.rs:9`. Takes 2-3 labeled options per question, same shape as `AskUserQuestion` (a free-form "Other" is added by the client, so do not list one). |
| Dispatch a subagent (`Agent` tool) | `spawn_agent` | `handlers/multi_agents/spawn.rs:25` (default protocol, see note below). |
| Message a running subagent (`SendMessage`) | `send_input` (default protocol) | `spec_plan.rs:670-674`. |
| Wait for a subagent's result | `wait_agent` | `spec_plan.rs:674`. |
| End a subagent | `close_agent` | `spec_plan.rs:674`. |
| `isolation: "worktree"` on the `Agent` tool | No isolation flag. Run `git worktree add` yourself before dispatch. | No matching hook or tool that creates a worktree found in `codex-rs`. |

### Two multi-agent protocol versions

Codex exposes subagent tools under one of two protocols, chosen by the
`multi_agent_v2` feature flag:

- **Default (V1)**, `multi_agent` feature, `stable true` per `codex features
  list` (no `~/.codex/config.toml` opt-in needed; this corrects the older
  pstack note that told you to set `[features] multi_agent = true` by hand).
  Tool names: `spawn_agent`, `send_input`, `wait_agent`, `resume_agent`,
  `close_agent` (`spec_plan.rs:670-674`).
- **V2**, `multi_agent_v2` feature, `stable false`, off by default. Tool
  names differ: `send_message` and `interrupt_agent` replace `send_input` and
  `close_agent` (`spec_plan.rs:676-682`). Only relevant if you (or a future
  Codex default) turn this flag on; check `codex features list` before
  trusting the V2 names.

### No equivalent found

- `Artifact` (publish a page to claude.ai). No web-publish tool in
  `codex-rs`.
- `ScheduleWakeup` / `Monitor` (scheduled or interval re-invocation). No
  scheduling tool; re-run the step yourself on a cadence, or use a Codex
  scheduled task if your environment has one.

## Model names

pstack-nikki's `models.json` gives each role a `models` object keyed by
harness (`claude`, `codex`, `copilot`), each value an ordered preference
list for that harness alone. On Codex, read the `codex` entry (`gpt-*`
slugs) and pin the first name in it; nothing here overrides that file.

## Driver and bundled skills

| Skill or driver named in pstack-nikki | On Codex |
|---|---|
| `run` (drive a CLI/TUI to see a change work) | Run the app yourself via `shell` and read the real output. |
| `loop` (recurring re-invocation, used by `babysit`) | No `loop` skill on Codex. Re-run the step yourself on a cadence, or use a Codex scheduled task if available. |

## Per-skill notes

These skills name a Claude-only tool directly and need the substitution
above. Most skills need only the table.

| Skill | Depends on | Codex substitution |
|---|---|---|
| `architect` | todolist | `update_plan` |
| `arena` | todolist; spawns N subagents in one message | `update_plan`; `spawn_agent` calls (concurrent) |
| `figure-it-out` | todolist | `update_plan` |
| `swarm` | todolist; spawns N workers in one message | `update_plan`; `spawn_agent` calls (concurrent) |
| `how` | `Agent` tool call fields (`agent`, `model`, `readonly`) | `spawn_agent` fields; `readonly` has no Codex equivalent, enforce it by instruction in the spawned agent's prompt |
| `interrogate` | spawns a reviewer panel, pins `model` per entry | `spawn_agent` per reviewer; take each reviewer's `codex` entry from `models.json` |
| `reflect` | spawns three `reviewer` agents in one message | `spawn_agent` calls (concurrent) |
| `why` | spawns investigator and synthesizer subagents | `spawn_agent` |
| `show-me-your-work` | pins the reviewer model via the spawn call's `model` argument | `spawn_agent`'s model argument |
| `rotate-agent` | messages a running agent, then spawns its successor | `send_input` (or `send_message` under V2), then `spawn_agent` |
| `blast-radius` | spawns one subagent per model in the `interrogate` reviewer roster | `spawn_agent` per model |

## Instructions file

Where a pstack-nikki skill says "your instructions file", on Codex that is
`AGENTS.md` (project root, plus `~/.codex/AGENTS.md` global). On Claude Code
it is `CLAUDE.md`.
