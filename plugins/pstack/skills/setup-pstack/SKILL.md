---
name: setup-pstack
description: Change which model a pstack role runs on without editing the repo. Writes the current harness's model override sheet in the user's home config directory, and wires it into the harness's global instructions. Use for /setup-pstack, "configure pstack models", or changing a role's model for this machine only.
---

# Setup pstack

The plugin's `models.json` holds the model picks for every pstack role. It is two directories up from this skill's directory. The [Models section of `poteto-mode`](../poteto-mode/SKILL.md#models) tells how each harness finds it. This skill writes an override sheet for the current harness. A row in the sheet replaces one role's list for this harness only. A role with no row keeps its `models.json` list.

The path of the sheet is its harness key. On Claude Code the sheet is `~/.claude/pstack-models.md`, and its rows override the `claude` lists only. On another harness, read [Other harnesses](#other-harnesses) for the sheet path and how it loads. The steps are the same.

## Steps

### 1. Detect available models

Enumerate the model slugs you can pass to the harness's spawn tool in this session. That is the dependable source. Compare them with this harness's `available` list in `models.json`, and mark each detected slug that the list does not hold. Ask the user to confirm any other slugs they want available. A slug that the user confirms and the harness accepts is valid for the sheet, even when it is not in `available`. That list constrains `models.json` only. Never write a real slug that was neither detected nor confirmed in step 1. The aliases `inherit-parent` and `auto` are always valid even though they are not detected slugs. Both mean that the role runs on the parent session's model, so the spawn call leaves out `model`.

### 2. Load current state

The defaults are this harness's lists in `models.json`, under `roles`. A role whose `models` is a string names a shared list under `panels`. If this harness's sheet already exists, read it and treat its rows as the current choices for the roles it names. Every other role keeps its `models.json` list. A row whose role is not in `models.json` `roles` is from a retired role. Drop it.

### 3. Map and confirm

Show every role with its list for this harness, with the sheet rows applied. Mark any real slug that step 1 did not detect or confirm as needing a choice. Also list each row that step 2 dropped. Ask whether to accept as-is or change specific roles, offering the detected and confirmed models plus `inherit-parent` and `auto` as the options. Prefer AskQuestion over free text.

Every value is a list in order of preference. A single-model role uses the first name. The [Models section of `poteto-mode`](../poteto-mode/SKILL.md#models) names the panel roles (arena runners, architect runners, interrogate reviewers). For a panel role, one subagent runs per entry, alias entries included, so the list length sets the count. `arena cross-judge pool` is also a list, but it is a single-model role. Arena selects one value from it whose model family differs from the parent's when possible. `swarm workers` is the default model for every worker unless a race or comparison assigns another model per arm.

`arena cross-judge pool` and `interrogate reviewers` share the `reviewer-panel` list in `models.json`. A sheet row for one of them overrides that role alone. Say so before you write, so the user knows that the two roles differ on this machine.

### 4. Validate

Every real slug written must be one that the harness accepts. That is a slug detected in step 1, or a slug that the user confirmed in step 1. It does not have to be in this harness's `available` list in `models.json`. `inherit-parent` and `auto` always pass. If a chosen real slug was not detected or confirmed in step 1, stop and ask again. Never write a slug of another harness. A `gpt-*` name in `~/.claude/pstack-models.md` still replaces the role's list. Claude Code rejects it, so the role falls through the rest of that list, then spawns unpinned, with a notice each time. In a panel role, the rejected seat is dropped instead.

### 5. Write the override sheet

Write this harness's sheet in the shape below, with this harness's own slugs. Overwrite the whole file so re-runs stay idempotent. Write a row for each sheet row that step 2 loaded and the user kept, and a row for each role that the user changed in this run. Write no row for a role that the user did not change and that had no row before. That role then gets each later change to `models.json`. A re-run where the user accepts everything as-is writes back the same rows.

A Claude Code sheet that changes three roles:

```markdown
# pstack model configuration

Per-role model overrides for pstack skills, for Claude Code only. The plugin's
`models.json` holds the picks for every role. A row here replaces that role's
list. Delete a row to use the `models.json` list again. Values are in order of
preference. A single-model role uses the first name, and a panel role runs one
subagent per entry. A value of `inherit-parent` or `auto` runs that role on the
parent session's model, and the spawn call leaves out `model`. An alias entry in
a panel list still counts toward that panel's fan-out.

feature, refactoring: opus, sonnet
swarm workers: haiku
interrogate reviewers: opus, sonnet, inherit-parent
```

A Codex sheet has the same shape with Codex slugs:

```markdown
feature, refactoring: gpt-6.1-sol, gpt-6-sol
swarm workers: gpt-5.6-terra
```

### 6. Wire it in

On Claude Code, if `~/.claude/CLAUDE.md` does not already include `~/.claude/pstack-models.md`, offer to append this line, so the rows load in every session:

```text
@~/.claude/pstack-models.md
```

That file is a user preference. Append only on an explicit yes, and change nothing else in it. If the user prefers project scope, add the include to the project's `CLAUDE.md` instead.

On Codex and Copilot CLI, paste the rows into the instructions file that [Other harnesses](#other-harnesses) names. These harnesses have no `@` include.

### 7. Confirm

Tell the user which harness's sheet you wrote, where it is, how its rows load, and which roles now differ from `models.json`. The sheet loads in new sessions. Re-running this skill rewrites this harness's sheet and leaves every other harness alone.

### 8. Offer a verification skill (optional)

Check whether the project has a way to drive the real app for proof (a `verify-*` skill, or an existing harness). If not, offer once: "want a project-local verification skill, so agents can drive the app the way a user does and prove changes work? I can generate one with /create-verification-skill." On yes, invoke `/create-verification-skill` (resolves wherever pstack is installed: workspace, user, or plugin). On no, move on without pushing.

## Other harnesses

The role rows are the same on every harness. The sheet path, the load method, and the model list differ. Detect models with the harness's own tool, and never write a slug that was neither detected nor confirmed in step 1. A harness whose spawn call has no model parameter still gets the sheet, as the record of the user's choice, and applies it where it can.

| Harness | Sheet | Load | List models | Overrides |
| --- | --- | --- | --- | --- |
| Claude Code | `~/.claude/pstack-models.md` | `@~/.claude/pstack-models.md` in `~/.claude/CLAUDE.md` | the spawn tool's model parameter | the `claude` lists |
| Codex | `~/.codex/pstack-models.md` | paste the rows into `~/.codex/AGENTS.md` | your configured Codex models | the `codex` lists |
| Copilot CLI | `<config-dir>/pstack-models.md` | paste the rows into `<config-dir>/copilot-instructions.md`. `<config-dir>` is `COPILOT_HOME` when it is set, otherwise `~/.copilot` | the CLI's documented model list | the `copilot` lists |
| opencode | `~/.config/opencode/pstack-models.md` | add the path to the `instructions` array in `opencode.json` | the `models` slash command in the session | none. `models.json` has no opencode key, so a role with no row spawns unpinned |
| Gemini CLI | `~/.gemini/pstack-models.md` | `@~/.gemini/pstack-models.md` in `~/.gemini/GEMINI.md` | the `model` slash command in the session | none. `models.json` has no Gemini CLI key, so a role with no row spawns unpinned |
