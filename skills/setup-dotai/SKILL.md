---
name: setup-dotai
description: The user invokes this by name after installing dotai, or to change which models delegated work runs on. Offers the harness preamble, then interviews them per label in the poteto-mode skill's models.md, validates each name against what the current harness can pin, and rewrites the confirmed rows so later spawns pick the new preferences.
---

# Setup dotai

## Preamble

Show the user these lines. Offer to add them to the harness's global
instructions file (`CLAUDE.md`, `AGENTS.md`, or equivalent). Append only
on a yes, skip lines already present, never edit anything else in that
file.

```
Load the `poteto-mode` skill before any non-trivial work.
Apply the `unslop` skill to every reply.
Use `caveman` ultra register for reasoning and for every message to or from
another agent.
```

## Copilot CLI

Copilot CLI keeps its own config directory and reads neither `CLAUDE.md`
nor a home-level `AGENTS.md`. Run this section only when setting dotai up
for Copilot CLI.

Resolve the config directory once: `COPILOT_HOME` when that variable is
set, otherwise `~/.copilot`. Never hardcode a home directory.

1. **Agents.** Copilot CLI loads user-level agents from
   `<config-dir>/agents/`, and only from files carrying an `.agent.md`
   extension. That path is its only documented user-level agent location,
   and a plugin install reports the skills it added and never the agents,
   so do not rely on the plugin's own `agents/` directory registering.
   Copy each file in this install's `agents/` directory to
   `<config-dir>/agents/<name>.agent.md`, frontmatter preserved verbatim.
   Create the directory when absent. Ask before overwriting a file that is
   already there.

2. **Instructions.** The global instructions file is
   `<config-dir>/copilot-instructions.md`, loaded on every session with no
   setting to enable. Append the Preamble lines above to it on an explicit
   yes, skipping any line already present. Create the file when absent.
   Change nothing else in it.

3. **Invocation.** Copilot CLI has no setting for a default agent; the
   request for one is `github/copilot-cli#2212`, still open. Tell the user
   to start a session with `copilot --agent zakia`, and that the CLI must
   be restarted before a newly copied agent is visible.

## Models

You edit the `poteto-mode` skill's `models.md` on the user's request. One
row per label, an ordered preference list of model names; a spawner walks
the list and pins the first name its harness accepts, so one row serves
every harness. Locate the file through the skills install this skill was
loaded from; never hardcode an install layout or guess a home directory.

1. **Discover the pinnable set.** Enumerate the model names the current
   harness accepts on a spawned agent this session (its spawn tool's model
   parameter, or its documented model list). That set, plus the harness
   aliases `models.md` maps to full names, is the only set you may write.
   Never write a name outside it, and never write one unconfirmed by the
   user.

2. **Load current state.** Read `models.md`; its rows are the current
   preference lists, one per label.

3. **Interview, per row.** Show the label and its current list. Ask which
   name goes first for this harness and whether any entry should move or go.
   No inline defaults, no assumed answer.

4. **Validate.** Reject any name outside the discovered set.

5. **Write.** Overwrite only the confirmed rows, in the same
   `label: comma-separated list` format. Leave every other line untouched.
   Report the path written and the rows changed.
