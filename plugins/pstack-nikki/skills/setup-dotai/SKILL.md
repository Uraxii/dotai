---
name: setup-dotai
description: The user invokes this after installing dotai, to install named agents for the current harness, or to change which models delegated work runs on. Offers the harness preamble, installs relative agent assets when needed, then validates and writes confirmed model preferences.
---

# Setup dotai

## Select the harness

Identify the harness running this skill and follow only its section below. If
dotai is already installed, do not repeat its install command. Resolve every
linked file from the directory containing this `SKILL.md`; never assume where
the plugin, repository, or home directory lives.

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

## Claude Code

Install dotai on a new machine:

```
/plugin marketplace add Uraxii/dotai
/plugin install pstack-nikki@Uraxii
```

Claude Code loads the plugin's agent files from
`../../agents/` automatically. Do not copy them into
`~/.claude/agents/`. It also loads the context-pressure hook from
`../../hooks/hooks.json`. Offer the Preamble for
`~/.claude/CLAUDE.md`, then continue to Models. Tell the user to start a new
session after changing the global instructions, agent definitions, or hooks.

## GitHub Copilot CLI

Install dotai on a new machine:

```
copilot plugin marketplace add Uraxii/dotai
copilot plugin install pstack-nikki@Uraxii
```

Copilot CLI keeps its own config directory and reads neither `CLAUDE.md`
nor a home-level `AGENTS.md`. Run this section only when setting dotai up
for Copilot CLI.

Resolve the config directory once: `COPILOT_HOME` when that variable is
set, otherwise `~/.copilot`. Never hardcode a home directory.

1. **Agents.** Copilot CLI loads the plugin's agent files from
   `../../agents/` automatically. Do not copy them into the
   personal `<config-dir>/agents/` directory.

2. **Hooks.** Copilot CLI loads the context-pressure hook from
   `../../hooks.json`. Do not copy it into the personal
   config directory.

3. **Instructions.** The global instructions file is
   `<config-dir>/copilot-instructions.md`, loaded on every session with no
   setting to enable. Append the Preamble lines above to it on an explicit
   yes, skipping any line already present. Create the file when absent.
   Change nothing else in it.

4. **Invocation.** Copilot CLI has no setting for a default agent; the
   request for one is `github/copilot-cli#2212`, still open. Tell the user
   to start a session with `copilot --agent zakia`, and that the CLI must
   be restarted before a newly installed plugin agent is visible.

## Codex

Install dotai on a new machine:

```
codex plugin marketplace add Uraxii/dotai --ref main
codex plugin add pstack-nikki@uraxii
```

Codex loads personal custom agents from `<codex-home>/agents/`. Resolve
`<codex-home>` from `CODEX_HOME` when set, otherwise use `~/.codex`.

1. Codex loads the plugin's context-pressure hook from
   `../../hooks/codex-hooks.json`. Tell the
   user to open `/hooks`, review the definition, and trust its current hash.
   Codex skips a new or changed plugin hook until the user trusts it.
2. Run [the Codex agent installer](scripts/install-codex-agents.py) with
   `--codex-home <codex-home>`. The script resolves
   [the generated agent files](assets/codex-agents/) relative to this skill and
   changes nothing when the installed files already match.
3. If the script reports a changed personal agent, show the paths and ask
   before rerunning with `--force`. The script checks every collision before
   it writes any agent file.
4. Offer Zakia as the main Codex persona. On a yes, add `--install-zakia`.
   This adds or refreshes an owned block in `<codex-home>/AGENTS.md` while
   preserving other global instructions. Report when a non-empty
   `AGENTS.override.md` masks that file.
5. Tell the user to start a new Codex session. Codex reads global instructions
   and custom-agent files when a session starts.

The generated Codex files intentionally omit `model` and
`model_reasoning_effort`. A custom-agent file would override the role choice
made by the spawning workflow. Keep model selection in `models.json` and pass
it when spawning instead.

The platform-neutral definitions live in
[references/agent-definitions.toml](references/agent-definitions.toml). After
changing that manifest or one of its relative instruction files, run
[the generator](scripts/generate-agent-configs.py). Do not edit generated
Claude or Codex agent files by hand.

## OpenCode

Install the skills on a new machine:

```
npx skills@latest add Uraxii/dotai
```

OpenCode does not consume this plugin's Claude or Codex agent definitions.
Do not copy them: OpenCode agent frontmatter and permissions have different
semantics. Use OpenCode's native subagent mechanism and put the dotai role in
the scoped brief. Offer the Preamble for
`~/.config/opencode/AGENTS.md`, then continue to Models. Start a new session
after changing global instructions or installed skills.

## Hermes

Register dotai as a skill source on a new machine:

```
hermes skills tap add Uraxii/dotai
```

Registering a tap does not install its skills. Install the dotai skills the
user wants from that tap; at minimum install `setup-dotai`, `poteto-mode`,
`unslop`, and `caveman`, followed by any roles or principles their workflow
uses. Keep every skill with its referenced support files.

Hermes has no dotai-specific named-agent files to install. Use its native
delegation and put the role in the scoped brief. Resolve `HERMES_HOME` when
set, otherwise use `~/.hermes`. Offer the Preamble for
`<hermes-home>/SOUL.md`, preserving the rest of the user's personality file,
then continue to Models. Start a new session after changing `SOUL.md` or
installed skills.

## Models

You edit `plugins/pstack-nikki/models.json` on the user's request. One row
per label, an ordered preference list of model names (or the name of a
shared list under `panels`); a spawner walks the list and pins the first
name its harness accepts, so one row serves every harness. Locate the file
through the skills install this skill was loaded from; never hardcode an
install layout or guess a home directory.

1. **Discover the pinnable set.** Enumerate the model names the current
   harness accepts on a spawned agent this session (its spawn tool's model
   parameter, or its documented model list). That set, plus `available` in
   `models.json`, is the only set you may write. Never write a name outside
   it, and never write one unconfirmed by the user.

2. **Load current state.** Read `models.json`; each `roles` entry's
   `models` is the current preference list for that label, resolving a
   named `panels` entry first.

3. **Interview, per row.** Show the label and its current list. Ask which
   name goes first for this harness and whether any entry should move or go.
   No inline defaults, no assumed answer.

4. **Validate.** Reject any name outside the discovered set.

5. **Write.** Update only the confirmed rows in `models.json`. Leave every
   other row untouched. Then run the generator so every skill's stamped
   Models block matches:

   ```
   python3 plugins/pstack-nikki/skills/setup-dotai/scripts/generate-models.py
   ```

   Report the rows changed and confirm
   `generate-models.py --check` exits 0.

## Auto mode: let agents use Proton Pass

In plain words: the auto-mode classifier has its own allow list, separate from `permissions.allow`. Without these two lines it blocks `pass-cli` and `secret-tool` for agents. User scope only, so add them to `~/.claude/settings.json`:

```
jq '.autoMode.allow = ((.autoMode.allow // []) + ["Reading, listing, and creating items in Proton Pass with pass-cli, and storing its access token in the OS keyring with secret-tool","Logging in to Proton Pass with pass-cli using the access token from the OS keyring"] | unique)' ~/.claude/settings.json > ~/.claude/settings.json.tmp && mv ~/.claude/settings.json.tmp ~/.claude/settings.json
```
