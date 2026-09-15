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

2. **Hooks.** Copilot CLI loads the context-pressure hook and the
   session-start reminder from `../../hooks.json`. Do not
   copy it into the personal config directory. The reminder's
   `additionalContext` output has a history of being dropped or replayed by
   the CLI (see README.md's Session-start reminder section); nothing to do
   about that here, it is wired per the current docs regardless.

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
   `../../hooks/codex-hooks.json`. Open `/hooks`, review the definition, and
   trust its current hash now: Codex skips a new or changed plugin hook
   until it is trusted, on this first install and after any later hook
   change.
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
made by the spawning workflow. Keep model selection in `models.json`: most
spawns omit `model` too, so the user's Codex `[agents]` defaults apply; a
spawn pinning from its own panel row (`interrogate` reviewers, the `arena`
cross-judge, the `blast-radius` panel) still pins from `models.json`.

The platform-neutral definitions live in
[references/agent-definitions.toml](references/agent-definitions.toml). After
changing that manifest or one of its relative instruction files, run
[the generator](scripts/generate-agent-configs.py). Do not edit generated
Claude or Codex agent files by hand.

### Updating

Refresh the installed plugin:

```
codex plugin marketplace upgrade uraxii
```

There is no `codex plugin update`. This command refreshes the marketplace
snapshot and reinstalls every plugin already installed from it, but it does
not touch `<codex-home>/agents/`. Rerun [the Codex agent
installer](scripts/install-codex-agents.py) only when
[assets/codex-agents/](assets/codex-agents/) changed: it changes nothing
when the installed files already match, and step 3 above covers showing the
changed paths before rerunning with `--force`. Start a new Codex session
after either step.

The hook trust hash covers the hook's event, matcher, and command, so a
plugin version bump alone keeps the existing trust. Re-trust the hook
through `/hooks` only when its event, matcher, or command changed.

## OpenCode

Install the skills on a new machine:

```
npx skills@latest add Uraxii/dotai
```

OpenCode does not consume this plugin's Claude or Codex agent definitions.
Do not copy them: OpenCode agent frontmatter and permissions have different
semantics. Use OpenCode's native subagent mechanism and put the dotai role in
the scoped brief.

**Session-start reminder.** OpenCode has no hook that fires once per session
and can inject text, so `../../hooks/opencode-reminder-plugin.ts`
pushes the reminder onto the system prompt before every LLM request instead
(`experimental.chat.system.transform`; see README.md's Session-start
reminder section for the sourcing). Symlink it, do not copy it, since it
looks up `session_start_context.py` as a sibling file at runtime:

```
mkdir -p ~/.config/opencode/plugin
ln -s "$(pwd)/plugins/pstack-nikki/hooks/opencode-reminder-plugin.ts" ~/.config/opencode/plugin/
```

Run from the cloned repo root. LIVE-UNVERIFIED: proven by a `node
--experimental-strip-types` load check in this repo's test suite, not by a
live OpenCode session.

Offer the Preamble for
`~/.config/opencode/AGENTS.md`, then continue to Models. Start a new session
after changing global instructions, installed skills, or the plugin.

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
set, otherwise use `~/.hermes`.

**Session-start reminder.** Hermes has no auto-discovered hook file the way
Claude Code and Codex do; add a `hooks:` block to the active profile in
`<hermes-home>/config.yaml` yourself, on an explicit yes (this is a user
config file, so ask first, same as the Preamble below):

```yaml
hooks:
  pre_llm_call:
    - command: "python3 <path-to-clone>/plugins/pstack-nikki/hooks/session_start_context.py --harness hermes"
```

Use the absolute path to the cloned repo's copy; Hermes does not require the
script to live under `~/.hermes/agent-hooks/`. The script reads Hermes's
`pre_llm_call` stdin payload and only emits `{"context": ...}` on
`extra.is_first_turn`, `{}` otherwise, so it injects once per session even
though the event itself fires on every turn (see README.md's Session-start
reminder section for the sourcing). The first run of this hook prompts the
user for consent, recorded in `<hermes-home>/shell-hooks-allowlist.json`; a
non-interactive setup can pass `--accept-hooks` or set
`HERMES_ACCEPT_HOOKS=1` instead. LIVE-UNVERIFIED: proven by unit tests
against the documented stdin/stdout shapes, not by a live Hermes session.

Offer the Preamble for
`<hermes-home>/SOUL.md`, preserving the rest of the user's personality file,
then continue to Models. Start a new session after changing `SOUL.md`,
`config.yaml`, or installed skills.

## Models

You edit `plugins/pstack-nikki/models.json` on the user's request. Each
`roles` entry's `models` is an object keyed by harness (`claude`, `codex`,
`copilot`), each value an ordered preference list, or the name of a shared
list under `panels`; a spawner reads the entry for its own harness and pins
the first name in it. `available` is keyed the same way: one label/slug
list per harness. Locate the file through the skills install this skill
was loaded from; never hardcode an install layout or guess a home
directory.

1. **Discover the pinnable set.** Enumerate the model names the current
   harness accepts on a spawned agent this session (its spawn tool's model
   parameter, or its documented model list). That set, plus this harness's
   list in `available`, is the only set you may write into this harness's
   entries. Never write a name outside it, and never write one unconfirmed
   by the user.

2. **Load current state.** Read `models.json`; each `roles` entry's
   `models` holds one ordered preference list per harness, resolving a
   named `panels` entry first.

3. **Interview, per row.** Show the label and its current list for this
   harness. Ask which name goes first and whether any entry should move or
   go. No inline defaults, no assumed answer.

4. **Validate.** Reject any name outside the discovered set, and any
   harness key outside `claude`, `codex`, `copilot`.

5. **Write.** Update only the confirmed harness entries in `models.json`.
   Leave every other row and every other harness untouched. Then run the
   generator so every skill's stamped Models block matches:

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
