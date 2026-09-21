---
name: setup-pstack
description: Change which model a pstack role runs on without editing the repo. Writes the current harness's model override sheet in the user's home config directory, and wires it into the harness's global instructions. Use for /setup-pstack, "configure pstack models", or changing a role's model for this machine only.
---

# Setup pstack

Model picks live in two places. `plugins/pstack/models.json` holds the
committed defaults, and every skill carries a stamped `## Models` block
listing them. This skill writes the other place: a per-harness **override
sheet** in the user's own config directory, loaded as session context, whose
rows win over the stamped defaults. Changing a model then touches no file in
the repo and needs no generator run.

On Codex, read the [platform mapping](../poteto-mode/references/codex-tools.md),
including its per-skill notes, before following this skill. On another
harness, read [Other harnesses](#other-harnesses) below for where the sheet
lives and how it loads; the steps are the same.

To edit the committed defaults in `models.json` instead, use `setup-dotai`.

## The sheet is per harness

`models.json` keys every role by harness (`claude`, `codex`, `copilot`), so
one role resolves to a different model on each. The override sheet keeps that
property without a harness column: **the path is the harness key.** A Claude
Code session reads `~/.claude/pstack-models.md`, and its rows override the
`claude` entries only. A Codex session reads `~/.codex/pstack-models.md`, and
its rows override the `codex` entries only. Neither can reach the other's
list, which is the point: a Codex row cannot silently become a Claude row.

Three rules follow, and there are no others:

- A row names slugs from this harness's `available` list in `models.json`, and
  nothing else.
- A role with no row keeps its `models.json` list for this harness.
- A role with neither a row nor a `models.json` entry for this harness spawns
  unpinned: the `Agent` call omits `model` and the child inherits the parent's.

Claude Code has no auto-applied "rules" mechanism like Cursor's `.mdc`.
Inclusion is explicit: the user adds a line to `~/.claude/CLAUDE.md` (or their
project `CLAUDE.md`) such as:

```text
@~/.claude/pstack-models.md
```

so the file is loaded as context for every session.

## Steps

### 1. Detect available models

Enumerate the model slugs you can pass to an `Agent` subagent in this session
— that is the dependable source. Cross-check them against this harness's
`available` list in [Models](#models) below. Ask the user to confirm or paste
any additional slugs they want available. Never write a real slug you have not
confirmed is available. The aliases `inherit-parent` and `auto` are always
valid even though they are not detected slugs; both mean the role runs on the
parent session's model, which the `Agent` call expresses by omitting `model`.

### 2. Load current state

The defaults are this harness's entries in [Models](#models) below. If this
harness's sheet already exists, read it and treat its rows as the current
choices for the roles it names. Every other role stays on the default.

### 3. Map and confirm

Show every role with its current list for this harness, marking any slug not
in the detected set as needing a choice. Ask whether to accept as-is or change
specific roles, offering the detected models plus `inherit-parent` and `auto`
as the options. Prefer `AskUserQuestion` over free text.

Every value is an ordered list. A single-model role takes the first name in
its list; a panel role (`arena runners`, `arena cross-judge pool`,
`interrogate reviewers`) runs one subagent per entry, alias entries included,
so the list length sets the count. `arena cross-judge pool` is a panel whose
values Arena picks one from, preferring a model family different from the
parent's. `swarm workers` is the default for every worker unless a race or
comparison assigns another model per arm.

`arena cross-judge pool` and `interrogate reviewers` share one list in
`models.json` (the `reviewer-panel` panel). Writing a row for one of them in
the sheet overrides that role alone; say so before writing, so the user knows
the two have come apart on this machine.

### 4. Validate

Every real slug written must be in the detected set and in this harness's
`available` list; `inherit-parent` and `auto` always pass. If a chosen slug is
not available, stop and ask again. Never write a slug belonging to another
harness — a `gpt-*` name in `~/.claude/pstack-models.md` pins nothing and
silently drops the role back to the default.

### 5. Write the override sheet

Write this harness's sheet with the shape below, filled with the harness's own
slugs. Overwrite the whole file so re-runs stay idempotent. Include only the
roles the user chose to override; a role left at its default belongs in no row.

The Claude Code shape, with this repo's current defaults as the example
values:

```markdown
# pstack model configuration

Per-role model overrides for pstack skills, for Claude Code only. The
committed defaults live in `plugins/pstack/models.json` and are repeated in
each skill's stamped Models section; the rows here override them. Delete a row
to fall back to the default. Values are ordered: a single-model role takes the
first, a panel role runs one subagent per entry. A value of `inherit-parent`
or `auto` runs that role on the parent session's model (the `Agent` call omits
`model`), and an alias entry in a panel list still counts toward that panel's
fan-out. Rows here apply to Claude Code alone; Codex reads
`~/.codex/pstack-models.md`.

codex watchers: sonnet
feature, refactoring: sonnet, opus
judgment and prose: opus, sonnet
arena runners: opus, sonnet
arena cross-judge pool: opus, sonnet
interrogate reviewers: opus, sonnet
swarm workers: sonnet
```

The Codex sheet is the same file with Codex slugs and no `codex watchers` row
(the watchers run on Claude Code, which is what spawns them):

```markdown
feature, refactoring: gpt-5.6-terra, gpt-5.6-sol
judgment and prose: gpt-5.6-sol, gpt-5.6-terra
arena runners: gpt-5.6-sol, gpt-5.6-terra
arena cross-judge pool: gpt-5.6-sol, gpt-5.6-terra
interrogate reviewers: gpt-5.6-sol, gpt-5.6-terra
swarm workers: gpt-5.6-terra
```

### 6. Wire it in

On Claude Code, if `~/.claude/CLAUDE.md` does not already include
`~/.claude/pstack-models.md`, offer to append the `@~/.claude/pstack-models.md`
line so the model rows load on every session. That file is a user preference:
append only on an explicit yes, and change nothing else in it. If the user
prefers project scope, add the include to the project's `CLAUDE.md` instead.

On Codex, paste the model rows into `~/.codex/AGENTS.md`; Codex has no `@`
include.

### 7. Confirm

Tell the user which harness's sheet you wrote, where it is, how its rows load,
and which roles now differ from the committed defaults. Re-running this skill
rewrites that harness's sheet and leaves every other harness alone.

## Other harnesses

The role rows are the same everywhere. What differs is the sheet path, how the
harness loads it, and how you list models. Detect models with the harness's
own tool and never write a slug you have not seen listed. A harness whose
subagent call has no model parameter still gets the sheet, as the record of
the user's choice, and applies it where it can.

| Harness | Sheet | Load | List models | Overrides |
| --- | --- | --- | --- | --- |
| Claude Code | `~/.claude/pstack-models.md` | `@~/.claude/pstack-models.md` in `~/.claude/CLAUDE.md` | the `Agent` tool's model parameter | the `claude` entries |
| Codex | `~/.codex/pstack-models.md` | paste the rows into `~/.codex/AGENTS.md` | your configured Codex models, see [codex-tools.md](../poteto-mode/references/codex-tools.md#model-names) | the `codex` entries |
| Copilot CLI | `<config-dir>/pstack-models.md` | paste the rows into `<config-dir>/copilot-instructions.md`; `<config-dir>` is `COPILOT_HOME` when set, otherwise `~/.copilot` | the CLI's documented model list | the `copilot` entries |
| opencode | `~/.config/opencode/pstack-models.md` | add the path to the `instructions` array in `opencode.json` | the `models` slash command in the session | no `models.json` harness key; the sheet is the record of the choice |
| Gemini CLI | `~/.gemini/pstack-models.md` | `@~/.gemini/pstack-models.md` in `~/.gemini/GEMINI.md` | the `model` slash command in the session | no `models.json` harness key; the sheet is the record of the choice |
