# What the harnesses actually hand a hook

In plain words: before writing the hook we installed a logging hook in both
Claude Code and GitHub Copilot CLI and looked at the real data each one sends.
This is what we saw, and which design decisions the measurements reversed.

Probed 2026-09-06. Raw captures: `/tmp/agent-isolation-probe/*.jsonl`.
Claude Code via two headless runs from a scratch repo. Copilot CLI mostly
BLOCKED, see the blocker section.

## Decisions the probes reversed

### 1. Main-checkout detection by string compare is wrong

The plan said: main checkout iff `git rev-parse --git-common-dir` is `.git`.
Measured, that is false from any subdirectory:

| cwd | `--git-common-dir` | `--git-dir` |
|---|---|---|
| main checkout root | `.git` | `.git` |
| main checkout subdir | `../.git` | `../.git` |
| linked worktree | `/abs/main/.git` | `/abs/main/.git/worktrees/<name>` |
| not a repo | non-zero exit, `fatal: not a git repository` | same |

An agent working in `repo/src/` would have walked straight through the gate.

Rule adopted instead: resolve both to absolute paths and compare.
`realpath(git-common-dir) == realpath(git-dir)` means main checkout. In a
linked worktree the git dir is always `<common>/worktrees/<name>`, so they can
never be equal. A non-zero exit means "not a repo", which passes.
Both calls run with `git -C <dir>` so the verdict never depends on the hook
process's own working directory.

### 2. A subagent's own transcript is not reachable at tool-call time

`PreToolUse` and `PostToolUse` carry `transcript_path`, but it is the MAIN
session's transcript, not the subagent's. Only `SubagentStop` carries
`agent_transcript_path`. Observed twice:

```
transcript_path            .../projects/<slug>/<session>.jsonl
agent_transcript_path      .../projects/<slug>/<session>/subagents/agent-<agent_id>.jsonl
```

That killed any plan to measure a subagent's context size from its transcript
during a tool call. The hook tells a subagent's calls from the main
thread's by the agent id instead, which needs nothing else.

### 3. Both harnesses read `hooks/hooks.json` out of an installed plugin, with
different schemas

Copilot auto-loads `hooks/hooks.json` from the plugin install directory
(proven live). Claude auto-loads `hooks/hooks.json` from the plugin root too.
Same filename, incompatible contents: Copilot wants camelCase events and a
`bash` key, Claude wants PascalCase events and a nested `hooks` array with a
`command` key.

Resolved by giving each harness its own file, with no manifest edit at all.
Measured: Copilot reads a `hooks.json` at the PLUGIN ROOT, reads
`hooks/hooks.json` when that is the only one present, and when BOTH exist reads
only the root file and silently ignores `hooks/hooks.json`. Claude's default is
`hooks/hooks.json`, auto-discovered, and it does not read a root `hooks.json`.

| File | Read by | Ignored by |
|---|---|---|
| `hooks.json` at repo root | Copilot CLI | Claude Code |
| `hooks/hooks.json` | Claude Code | Copilot, because the root file wins |

`.claude-plugin/plugin.json` needs no `hooks` key. The override key exists (the
installed `ponytail` plugin uses `"hooks": "./hooks/claude-codex-hooks.json"`)
but this split does not need it.

Do not "simplify" this back into one shared file. Copilot supports a PascalCase
dialect of event names for Claude-plugin compatibility, so a merged file
carrying both `sessionStart` and `SessionStart` fired the hook TWICE in one
run, once per casing, with two different payload shapes: camelCase
`sessionId` / `initialPrompt` against snake_case `session_id` /
`initial_prompt`. Copilot raises no error on unknown keys, so the merged file
looks healthy and misbehaves quietly.

## Claude Code

### Q1. Does a subagent's tool call identify the subagent? Yes.

Every event carries `agent_id` and `agent_type`. The main thread has
`agent_id: null` while still carrying an `agent_type` (the main persona name),
so the subagent test is `agent_id != null`, never `agent_type` presence.

Captured `PreToolUse`, one run, in order:

```
agent_id            agent_type        tool_name
null                zakia             Skill
null                zakia             Agent
a42a25ff16747bac5   general-purpose   Bash
a42a25ff16747bac5   general-purpose   Bash
a42a25ff16747bac5   general-purpose   Write
a42a25ff16747bac5   general-purpose   Bash
```

`agent_id` is stable across all of one subagent's calls, so it is the counter
key. On the main thread the counter keys on `session_id`.

### Q2. Is the subagent's own transcript reachable? Not during a tool call.

See "Decisions the probes reversed", item 2.

### Q3. Does `Agent` `tool_input` carry `isolation`? Yes, when asked for.

Absent on a plain spawn. Present verbatim as `"worktree"` when the spawn
requested worktree isolation, confirmed functionally by the subagent's own
`pwd` landing under `.claude/worktrees/`. The hooks reference does not list the
field; the wire does carry it.

### Q4. Does `SubagentStop` fire? Yes, once per subagent.

Keys: `agent_id`, `agent_transcript_path`, `agent_type`, `background_tasks`,
`cwd`, `effort`, `hook_event_name`, `last_assistant_message`,
`permission_mode`, `prompt_id`, `session_crons`, `session_id`,
`stop_hook_active`, `transcript_path`.

Recorded for completeness. The hook does not use this event: blocking a stop
was cut from scope.

### Q5. Does `PostToolUse` `additionalContext` reach a subagent? Yes.

A sentinel emitted by the hook on a subagent's own `Bash` call came back
quoted verbatim in that subagent's final answer, and the sentinels emitted on
main-thread calls did not. Recorded for completeness. Context injection was
cut from scope: the hook only ever denies, and a denial reason is a channel
the model always sees.

### Claude hook wiring, measured

- Project-scope `.claude/settings.json` hooks fire for headless `claude -p`
  runs started in that directory, including for its subagents.
- `PreToolUse` still fires for calls the sandbox later refuses, and no
  matching `PostToolUse` follows. A hook must not assume the two pair up.

## GitHub Copilot CLI

### BLOCKED: account quota exhausted

Every `copilot -p` run failed at the model call, before any tool ran:

```
{"errorType":"quota","message":"You have exceeded your monthly quota",
 "statusCode":402,"errorCode":"quota_exceeded"}
"premium_interactions":{"entitlementRequests":1500,"usedRequests":1500,
 "remainingPercentage":0,"resetDate":"2026-10-01T00:00:00Z"}
```

Tried on `claude-sonnet-5`, `--model auto` (routed to `mai-code-1.1-flash`,
same quota) and `claude-haiku-4.5`. `gpt-4.1` was unavailable. Auto-routing
does not dodge the quota.

Consequence: `preToolUse`, `postToolUse`, `subagentStart`, `subagentStop` and
`agentStop` never fired, so their runtime shapes are UNVERIFIED here and the
hook codes against the documented shapes instead. Re-run after 2026-10-01, or
with a different token, using the ready-made configs in
`/tmp/agent-isolation-probe/hooks-main.json`.

### What did fire: `sessionStart`

It runs at session bootstrap, before the model call, so it survives the quota
block:

```json
{"sessionId": "d27ddab2-d476-4954-a127-8a6db821601c", "timestamp": 1788720969504,
 "cwd": "/var/home/nicole/Projects/nikki-net", "source": "new",
 "initialPrompt": "say hi"}
```

All camelCase, matching the documented pattern. It is enough to prove hook
CONFIG LOADING, which is how the plugin question below got answered.

### Q11. Does installing the plugin wire the hooks? Yes, with no manual copy.

Proven live. A `sessionStart` logger placed at the plugin's
`hooks/hooks.json` fired alongside a control config in `~/.copilot/hooks/`,
in the same run, same session id. Both sources combine; neither replaces the
other.

Two findings that shape the install:

- A `.copilot/hooks/` folder nested inside the plugin does NOT fire. It is not
  a source Copilot reads.
- There is no `${CLAUDE_PLUGIN_ROOT}` equivalent, and none is needed: a plugin
  hook's `bash` command runs with its working directory already set to the
  plugin's own install directory. A probe echoed
  `cwd_at_run = /var/home/nicole/.copilot/installed-plugins/Uraxii/dotai`.
  So the shipped config uses a relative path and never hardcodes the
  marketplace owner segment.

### Documented shapes the hook codes against, NOT observed here

From the stored Copilot hooks reference (kb source S7):

- `preToolUse` / `postToolUse` stdin: `{sessionId, timestamp, cwd, toolName, toolArgs}`,
  `toolArgs` typed `unknown`.
- Built-in tools: `ask_user, bash, create, edit, glob, grep, powershell, task,
  view, web_fetch`.
- Deny: stdout `{"permissionDecision":"deny","permissionDecisionReason":"..."}`.
  The reference confirms `permissionDecisionReason` is shown to the model, so a
  denial reason is a channel the agent always reads.
- Command hooks are fail-CLOSED on any non-zero exit, and fail-OPEN on timeout.

The fail-closed rule is why every hook path exits 0 and says "deny" in JSON
instead of exiting non-zero: an unexpected crash must not deny every tool call
in the session.

## Still open

- Copilot `toolArgs` key names per tool. Needed to know which field holds the
  path for `create`/`edit` and the command string for `bash`. Coded against the
  documented shape with a tolerant reader; re-probe after 2026-10-01.
- Whether Claude Code ignores a repo-root `hooks.json` as expected. Copilot's
  side of the split is measured; Claude's side is inferred from its documented
  default path plus the absence of any doc mentioning a root file.

## Decisions coded

- **Copilot applies to every call (open).** Copilot's `preToolUse` payload
  carries no agent id, so `agent_isolation.py` cannot tell a helper's call from the
  user's own; it denies a main-checkout write on every call regardless.
  Revisit if a Copilot payload with an agent id ever turns up.
- **Bash mutation check is a blocklist (hypothesis).** `agent_isolation.py` denies a
  `Bash`/`bash`/`powershell` call in the main checkout only when the command
  matches a mutating pattern: a redirect, `rm`/`mv`/`cp`/`touch`/`mkdir`/
  `tee`, `sed -i`, or a mutating `git` subcommand. Everything else passes,
  so a read-heavy agent (`git log`, `grep`, `cat`) never gets blocked.
  Extend the pattern set if a real mutating command slips through.
- **No tool-call limit.** The user decided job sizing is not a watcher's job
  and had the hook's tool-call limit removed, so sizing is now handled by
  the `principle-decomposition` skill.
