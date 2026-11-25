# Guideline hooks design

Spec for the Claude Code hooks that deliver code-quality guidelines. An
implementer follows it without asking. Status: design only, nothing built.

Inputs read for this spec:

- `.ai/code-quality-lint-plan.md`, section "Revised design".
- `.ai/guideline-mapping.md` (the planned guidelines and detectors).
- `plugins/pstack/skills/principle-code-quality/` (`SKILL.md`, `languages.toml`, `scripts/code_quality.py`, `scripts/test_code_quality.py`).
- Hook conventions in `plugins/*/hooks/`, `scripts/run-hook-tests.sh`, `scripts/hook-test-assertions.sh`.
- The OX VibeSec reference wiring, `hooks/hooks.json` in the ox-vibesec 1.2.0 plugin cache.
- Claude Code docs: <https://code.claude.com/docs/en/hooks> and <https://code.claude.com/docs/en/tools-reference>, read 2026-11-25.
- Codex hooks docs: <https://learn.chatgpt.com/docs/hooks> (redirect target of developers.openai.com/codex/hooks), read 2026-11-25.
- Copilot CLI hooks docs: <https://docs.github.com/en/copilot/reference/hooks-configuration>, read 2026-11-25.
- Per-harness wiring in this repo: `README.md` (Install, Session-start reminder), `scripts/generate-plugin-manifests.py` (`ALL_HARNESSES`, `on_harness`, `codex_manifest`, `HOOK_WIRING_PATHS`), `plugins/pstack/hooks/{hooks,codex-hooks,copilot-hooks}.json`, `plugins/pstack/.codex-plugin/plugin.json`, `plugins/pstack/.github/plugin/plugin.json`, `plugins/pstack/pi/*.ts`, `plugins/skills/hooks/skill-quality-guidance`, `plugins/shunt/hooks/check-bash-read`. `as_claude_plugin_agent` and `render_profiles` live in `scripts/sync-codebase-memory-upstream.py` and render agent files, not hooks, so they do not affect this design.

Labels used below:

- **[docs]** means verified from the Claude Code docs pages above. **[codex-docs]** and **[copilot-docs]** mean verified from those vendors' pages above.
- **[repo]** means verified from code in this repo, with the file named.
- **[measured]** means run on this machine during this investigation.
- **[guess]** means not verified. The implementer checks it in unit 1 of the plan.

## Requirements

1. Hooks search the guideline metadata to pick guidance deterministically. The same inputs and state give the same output.
2. Triggers are language detection, detector findings, and keywords. No vectors (see open question 8).
3. Fire only in the correct context: right language, right tool event, code files only, not on paths a guideline excludes (tests, docs), not on unrelated prompts.
4. Error bias: a false negative (a gap) is worse than a false positive. When unsure, deliver the guideline as a warning. Block only on an unambiguous detector hit that the pending edit introduces.
5. Global guidelines go out when a language is first detected. Contextual guidelines go out when their detector or keyword fires. A guideline sent recently is not sent again. A guideline with `enabled: false` never fires, and its detectors do not run.
6. Detectors are open source CLI tools only: `ruff`, `pylint`, `mypy`, `eslint`, `lizard`, `complexipy`, `opengrep`/`semgrep`, `gdlint`, the dotnet analyzers (Roslyn, StyleCop.Analyzers), and our own `code_quality.py`. No proprietary or hosted service. Hooks may also use what the harness itself provides: its hook types (including `prompt` and `agent` hooks), the session's own model, and harness-provided input fields and environment variables. A missing tool gives a visible notice, and its guidelines go out as warnings (C, "Tool missing").
7. The hooks work on every harness dotai supports, not only Claude Code. One harness-neutral core holds guideline search, language detection, the detector runner, and dedupe state. A thin adapter per harness maps that harness's events in and out. Where a harness lacks an event, the delivery degrades to a stated fallback, never to silence. Skill-frontmatter hooks are not used: they are Claude Code only and start only after the skill loads.

## Facts this design rests on

Claude Code hooks:

- Events used here exist: `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`. Also available but not used: `PostToolUseFailure`, `PostToolBatch`, `SubagentStart`, `SubagentStop`, `Stop`, `PreCompact`, `PostCompact`, `FileChanged`, `SessionEnd`, and more. [docs]
- Common input fields are `session_id`, `transcript_path`, `cwd`, `hook_event_name`, `permission_mode`. Inside a subagent the input also carries `agent_id` and `agent_type`. [docs]
- Plugin hooks run inside subagents. `PreToolUse` and `PostToolUse` fire for a subagent's tool calls with `agent_id` set. [docs] Whether `UserPromptSubmit` fires inside a subagent is not stated. [guess: it does not]
- Whether a subagent's `session_id` equals the parent's is not stated. [guess: it does] State is keyed by `agent_id` as well, so the design works either way.
- `PreToolUse` input has `tool_name`, `tool_input`, `tool_use_id`. Write input is `file_path` (absolute) and `content`. Edit input is `file_path`, `old_string`, `new_string`, `replace_all`. [docs]
- `MultiEdit` is not in the current tools reference. The current file tools are `Edit`, `Write`, `NotebookEdit`. [docs] Its input shape (`file_path`, `edits` list of `{old_string, new_string, replace_all}`) is [guess]. Keep `MultiEdit` in the matcher because `plugins/steer` already matches `Write|Edit|MultiEdit`, and it costs nothing.
- Edit does exact string replacement. `old_string` must appear exactly once unless `replace_all` is true. The Edit tool refuses a file that is not valid UTF-8. [docs]
- `PreToolUse` output `hookSpecificOutput.permissionDecision: "deny"` prevents the call, and `permissionDecisionReason` is shown to Claude. Exit code 2 routes the same way, with stderr as the reason. [docs]
- `PreToolUse` and `PostToolUse` `additionalContext` is added next to the tool result. So context from `PreToolUse` reaches Claude after the write, not before it. [docs]
- `PostToolUse` input adds `tool_response`. Its `decision: "block"` only adds `reason` next to the result. The tool already ran. [docs]
- `UserPromptSubmit` input has `prompt`. `additionalContext` is added alongside the prompt. It also fires on turns Claude Code starts on its own. [docs]
- `SessionStart` matcher values are `startup`, `resume`, `clear`, `compact`, `fork`. Input field `source` carries the same value. `additionalContext` is added at the start of the conversation. [docs]
- `systemMessage` is a warning shown to the user. [docs]
- `additionalContext`, `systemMessage`, and plain stdout are capped at 10,000 characters. Over the cap, Claude Code saves the text to a file and shows a 2,000-character preview. [docs]
- Default timeout for a command hook is 600 s, lowered to 30 s on `UserPromptSubmit`. Hook `timeout` is in seconds. [docs] Repo hooks set `"timeout": 10` (`plugins/steer/hooks/claude-hooks.json`).
- Matching hooks for one event run in parallel. [docs]
- Hook processes get `CLAUDE_PLUGIN_ROOT`, `CLAUDE_PROJECT_DIR`, and `CLAUDE_PLUGIN_DATA`. `CLAUDE_PLUGIN_DATA` is the plugin's persistent data directory and survives plugin updates. [docs]
- `Stop` input has `stop_hook_active`, true when Claude Code is already continuing because of a stop hook. [docs]
- Hook handler types are `command`, `http`, `mcp_tool`, `prompt`, `agent`. A `prompt` hook sends `$ARGUMENTS` (the hook input JSON) plus a fixed prompt to a Claude model (default: the background model) for one turn and gets back `{"ok", "reason"}`. An `agent` hook is the same with up to 50 tool-using turns, and is marked experimental. Default timeouts are 30 s (`prompt`) and 60 s (`agent`). [docs]
- `prompt` and `agent` hooks work on `PreToolUse`, `PostToolUse`, `UserPromptSubmit`, `Stop`, `SubagentStop`, and others. `SessionStart` supports only `command` and `mcp_tool`. `SubagentStart`, `PreCompact`, `PostCompact` do not support `prompt` or `agent`. [docs]
- On `ok: false`, a `PreToolUse` prompt hook denies the call and by default ends the turn. With `continueOnBlock: true` the reason goes back to Claude as the tool error. On `PostToolUse` and `UserPromptSubmit`, `ok: false` ends the turn by default. A prompt hook has no way to add warn-level context. It returns only allow or block. [docs]
- The common `if` field takes one permission rule such as `"Edit(*.ts)"` and skips the hook when the tool call does not match. It works only on tool events, takes no lists, and is "best-effort". [docs]

This repo:

- Hooks in this repo need only bash and awk, and tests run each hook as a subprocess with `jq` stubbed to fail (`scripts/hook-test-assertions.sh`). [measured: read the file]
- This system deviates on purpose. It needs Python 3.11 or later, because `tomllib` reads `languages.toml` and `code_quality.py` is Python. The bash wrapper keeps the repo convention for entry and Windows lookup. Python is the engine. Open question 6 covers this.
- `plugins/pstack/hooks/hooks.json` is the Claude Code wiring for pstack and today holds only `SessionStart`. [measured]
- The repo has no `.github/workflows`, so no CI runs the tests. `scripts/run-hook-tests.sh` runs every `plugins/*/hooks/tests/*.test.sh`. [measured]

Local tools on this machine [measured]:

| Tool | State | One run, wall time |
| --- | --- | --- |
| `python3` | 3.13.18 | 45 ms to import `tomllib, ast, json, subprocess` |
| `code_quality.py` | ships in the skill | 40 ms on a 2-line file |
| `ruff` | 0.16.9 | 227 ms, `--output-format=json`, stdin |
| `eslint` | 10.1.0 | 145 ms, `--stdin --no-config-lookup --rule` |
| `mypy`, `tsc`, `node` | installed | not timed |
| `pylint`, `lizard`, `complexipy`, `gdlint`, `dotnet`, `ast-grep` | missing | |
| `sg` | present, but it is the shadow-utils group command, not ast-grep | |

The `sg` row matters. A runner must confirm a tool by its version output, not by `command -v` alone.

Numbers come from one run each. They are a budget guide, not a benchmark.

### Harness features versus command hooks

Requirement 6 also allows harness features. This is where each one wins or loses against a command hook.

| Harness feature | Use it? | Why |
| --- | --- | --- |
| `additionalContext` into the session's own model | Yes, the core delivery path | The session model reads the guideline body and applies the judgment. This is the cheapest way to use a model: no extra call, no latency |
| `systemMessage` | Yes, for notices | Shows a missing-tool or failure notice to the user, so a gap is never silent [docs] |
| `CLAUDE_PLUGIN_DATA` | Yes, for session state | Persistent per-plugin directory that survives updates [docs]. No state store of our own |
| `agent_id` in tool-event input | Yes, for per-agent state | Tells a subagent's call from the main thread's [docs] |
| `stop_hook_active` | Yes, in optional unit 12 | Stops a Stop hook from blocking in a loop [docs] |
| `prompt` hook on `PreToolUse` for guidelines | No | Each write would cost one model call, up to 30 s, far over the 2.5 s budget in E. The verdict is not deterministic (requirement 1). A deny from a model guess is not "an unambiguous detector hit" (requirement 4). The prompt text is fixed in `hooks.json`, so it cannot pick guidelines from metadata |
| `prompt` hook on `PostToolUse` or `UserPromptSubmit` | No | It can only allow or block, and block ends the turn by default. It cannot deliver a warning as context, which is most of this system |
| `agent` hook on `Stop` or `SubagentStop` | Candidate, not in v1 (open question 7) | The one place a model pass beats a command hook. At end of turn, an agent hook could read the changed code files and the global guidelines for their languages, and judge the guidelines that have no detector. It costs up to 60 s per stop, is experimental, and is not deterministic, so it stays warn-only (`ok: false` makes Claude continue with the reason) |
| `if` filter, such as `"Edit(*.py)"` | No | One rule per hook entry, no lists. Covering every extension in `languages.toml` needs dozens of entries. The engine filters by language in 45 ms anyway |
| `async: true` | No | An async hook cannot block [docs], and the gate must block |

## Harnesses

### Which harnesses dotai supports, and how hooks ship

| Harness | How dotai ships to it | Hook wiring for pstack | Source |
| --- | --- | --- | --- |
| Claude Code | Plugin marketplace | `plugins/pstack/hooks/hooks.json` (default path, no manifest key) | [repo] `README.md` Session-start reminder, `generate-plugin-manifests.py` comment at the ox-vibesec entry |
| Codex CLI and app | Plugin marketplace. The user must trust plugin hooks through `/hooks` first | `plugins/pstack/hooks/codex-hooks.json`, named by `.codex-plugin/plugin.json` `"hooks"` | [repo] `README.md`, `.codex-plugin/plugin.json` line 31 |
| Copilot CLI | Plugin marketplace | `plugins/pstack/hooks/copilot-hooks.json`, named by `.github/plugin/plugin.json` `"hooks"` | [repo] `.github/plugin/plugin.json` |
| Pi | pstack Pi extension, TypeScript | `plugins/pstack/pi/index.ts` registers `pi.on(...)` handlers | [repo] `README.md` table, `pi/index.ts` |
| opencode, Hermes, Gemini CLI, Cursor and other skills.sh targets | Skills only (`npx skills@latest add`, `hermes skills tap add`, or a skills directory) | None. "They get no session-start reminder from this repo" | [repo] `README.md` Install and Session-start reminder |

`ALL_HARNESSES = ["claude", "codex", "copilot"]` in `generate-plugin-manifests.py` is the manifest set. Pi rides on the pstack extension, and the rest get skills only [repo].

### Per-harness hook contract

| | Claude Code | Codex | Copilot CLI | Pi |
| --- | --- | --- | --- | --- |
| Events we need | `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse` [docs] | `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PreCompact`, `PostCompact`, `SubagentStart`, `Stop` exist [codex-docs] | `sessionStart`, `userPromptSubmitted`, `preToolUse`, `postToolUse`, `preCompact`, `subagentStart`, `agentStop` exist [copilot-docs] | `session_start`, `before_agent_start`, `tool_call`, `tool_result` [repo] `pi/index.ts`, `pi/prompt.ts`, `pi/agent-tools.ts`, `pi/path-skills.ts` |
| File-write tools | `Write`, `Edit`, (`MultiEdit`) [docs] | `apply_patch`, patch text in `tool_input.command` with `*** Add File:` / `*** Update File:` / `*** Move to:` headers [repo] `skills/hooks/skill-quality-guidance`; [codex-docs] says `PreToolUse` intercepts `apply_patch` | `edit`, `create` [copilot-docs]. Path in `toolArgs.path` [repo] `skill-quality-guidance`. Other arg names [guess: `old_str`, `new_str`, `file_text`] | `write`, `edit` (exact text replacement) [repo] `pi-tools.md`. Path in `event.input.path` [repo] `path-skills.ts`. Edit text fields [guess] |
| Read tool | `Read` [docs] | none. Reads go through shell [guess] | `view` [repo] `copilot-hooks.json` matcher | `read` [repo] `path-skills.ts` |
| Payload shape | `tool_name`, `tool_input`, `session_id`, `cwd` [docs] | same as Claude: `tool_input`, `session_id`, `cwd` [repo] `skill-quality-guidance` | `toolName`, `toolArgs` (a JSON string), `sessionId` [repo] `skill-quality-guidance`, `shunt/hooks/check-bash-read`; Claude-format input on PascalCase hook names [repo] `pstack/hooks/pre-tool-use.awk` comment | JS event objects: `event.toolName`, `event.input`, `ctx.cwd` [repo] |
| Block a write | `hookSpecificOutput.permissionDecision: "deny"` [docs] | same shape, or exit 2 [codex-docs]; [repo] `check-bash-read` emits the Claude shape for codex | top-level `{"permissionDecision":"deny","permissionDecisionReason":...}` [copilot-docs], [repo] `check-bash-read` | return `{ block: true, reason }` from `tool_call` [repo] `agent-tools.ts` |
| Context before or at the write | `PreToolUse` `additionalContext` [docs] | `PreToolUse` `additionalContext` [codex-docs], [repo] `skill-quality-guidance` | none: `preToolUse` has no context field [copilot-docs] | none at `tool_call` [guess] |
| Context after a write or read | `PostToolUse` `additionalContext` [docs] | `PostToolUse` `additionalContext` [codex-docs]. Whether it fires for `apply_patch` [guess: yes] | `postToolUse` `{"additionalContext": ...}` [copilot-docs], [repo] `skill-quality-guidance` | `tool_result` returns `content` with text appended [repo] `path-skills.ts` |
| Context at prompt | `UserPromptSubmit` `additionalContext` [docs] | `UserPromptSubmit` `additionalContext` or plain stdout [codex-docs] | none: command `userPromptSubmitted` output is dropped [copilot-docs] | `before_agent_start` sets system-prompt sections every agent start [repo] `prompt.ts`. Prompt text in that event [guess] |
| After compaction | `SessionStart` `compact` [docs] | `SessionStart` `compact`, runs after root-session compaction [codex-docs] | `sessionStart` sources are `startup`, `resume`, `new`, no compact. `preCompact` exists [copilot-docs] | `before_agent_start` runs again, so compaction cannot drop its sections [repo] `prompt.ts` comment |
| Message to the user | `systemMessage` [docs] | not documented [guess: none] | not documented [guess: none] | `ctx.ui` notify [guess] |
| Subagents | tool hooks fire with `agent_id` [docs] | `SubagentStart`/`SubagentStop` exist; tool hooks inside subagents not stated [codex-docs] | `subagentStart` exists; tool-hook identity in subagents not stated [copilot-docs] | child agents are separate `pi` processes that load the extension with a depth flag [repo] `pi/index.ts`, `pi/config.ts` |
| Root and data dirs | `CLAUDE_PLUGIN_ROOT`, `CLAUDE_PLUGIN_DATA` [docs] | `PLUGIN_ROOT`, `PLUGIN_DATA`, and `CLAUDE_PLUGIN_ROOT`, `CLAUDE_PLUGIN_DATA` for compatibility [codex-docs] | `COPILOT_PLUGIN_ROOT` [repo] `copilot-hooks.json`. No data dir documented [guess] | `settings.pluginRoot` [repo] `prompt.ts` |
| Timeout and failure | default 600 s, 30 s on `UserPromptSubmit` [docs] | default 600 s [codex-docs] | `timeoutSec` default 30 s, timeouts fail open. A `preToolUse` hook that exits 2 or crashes denies the call [copilot-docs] | in-process handler [repo] |
| Windows | `bash` via Git Bash, `run-hook.cmd` [repo] | `commandWindows` [codex-docs], [repo] `pstack/hooks/codex-hooks.json` | `powershell` key [repo] `scripts/hook-test-assertions.sh` `windows_commands` | Node, cross-platform |

### Core and adapters

The core is harness-neutral and never reads a harness payload. It takes one neutral event on stdin and returns one neutral result.

```
NeutralEvent (JSON):
  kind:     "session_start" | "compacted" | "prompt" | "pre_write" | "post_write" | "post_read"
  session:  str        # harness session id
  agent:    str        # "main" or a subagent key
  cwd:      str
  root:     str        # project root for relative paths and globs
  prompt:   str        # kind "prompt" only
  files:    [{"path": str, "before": str | null, "after": str | null}]
            # pre_write: before = disk text or null, after = built post-edit text
            # post_write, post_read: after = disk text, before = null

NeutralResult (JSON):
  deny:     str | null   # pre_write only; the deny reason text from "Output formats"
  context:  str | null   # the additionalContext text from "Output formats"
  notice:   str | null   # notices only, for a user-visible channel
```

Each adapter does three things: map its payload to a `NeutralEvent` (including building `after` for a pending write), call the core, and render the `NeutralResult` in its own output shape. When the harness cannot show a field, the adapter applies the fallback in the degradation table below. The core owns dedupe, so a fallback that delays delivery (a queue) lives in core state, not in an adapter.

- Python adapters for Claude Code, Codex, and Copilot CLI: `guideline_hook.py --harness claude|codex|copilot`, the same `--harness` pattern as `skill-quality-guidance` and `check-bash-read` [repo].
- Pi adapter: `plugins/pstack/pi/guidelines.ts`. It builds a `NeutralEvent` in TypeScript and runs `python3 -I guideline_hook.py --harness neutral` with `child_process.spawnSync` (stdin JSON, 3 s timeout). Pi already ships Node; the core stays in one language.
- No-hook harnesses: `guideline_hook.py check PATH...` prints the guidelines and findings for those files in the same text format and exits 1 when a `block` finding exists. The skill prose tells the agent to run it (unit 11).

New core state field for the fallbacks: `pending: [guideline_id, ...]`, ids picked by a trigger whose harness had no channel at that moment. The next event with a context channel delivers them first, then clears them.

### Degradation by harness

"Native" means the harness has the event and the output field. Each fallback still delivers. None drops a guideline.

| Delivery | Claude Code | Codex | Copilot CLI | Pi | Skills-only harnesses |
| --- | --- | --- | --- | --- | --- |
| Globals on first language detection | Native, at `Read` (`PostToolUse`) or at first write (`PreToolUse`) | At first `apply_patch` (`PreToolUse` context). No Read hook, so globals arrive with the first write, not before it. Prompt file paths also detect | At `view` or first `edit`/`create` (`postToolUse`), so after the first write | Native, at `read`/`write`/`edit` (`tool_result`), and as a system-prompt section from then on (`before_agent_start`) | The skill tells the agent to run `check` before and after editing; `check` prints globals |
| Block on a new `block` hit | Native deny | Native deny. Post-edit text comes from applying the patch in memory. If the patch cannot be applied, no gate; the hit arrives as a warning after the write | Native deny. Arg names are [guess]; if `after` cannot be built, no gate and the hit arrives as a warning after the write | Native block. If edit fields cannot be read, warning after the write | No gate. `check` exits 1 and the skill says to fix before continuing. Agent-dependent, high false-negative risk |
| Warn findings after a write | Native | Native if `PostToolUse` fires for `apply_patch` [guess]. Else they are queued in `pending` and the next `PreToolUse` context carries them | Native | Native | `check` output |
| Prompt keywords and prompt file paths | Native | Native | No channel. Picked ids go to `pending`, delivered at the next `postToolUse` | At `before_agent_start` if it carries the prompt [guess]; else nothing until a file touch | Not available |
| Re-send after compaction | `SessionStart` `compact` | `SessionStart` `compact` | `preCompact` clears `sent` and puts the detected languages' globals in `pending`; the next `postToolUse` delivers them | Native: the system-prompt section is set again at every agent start | Not applicable |
| Missing-tool notice to the user | `systemMessage` plus context | Context only; the model sees it and can tell the user | Context only, at `postToolUse` (pre-tool has no channel, so the notice waits in `pending`) | Context via `tool_result`, plus `ctx.ui` notify if it exists [guess] | `check` prints it |
| Separate state per subagent | `agent_id` [docs] | Key by `session_id`; if subagents share it, a subagent may miss globals the parent got [guess]. Unit 1 checks | Same as Codex | Separate process with a depth flag; key `agent` = `depth-<n>-pid-<pid>` | Not applicable |
| Bash-written files | Optional `Stop` command hook (unit 12) | Optional `Stop` hook, same design | Optional `agentStop` hook, `decision: "block"` [copilot-docs] | Optional handler on `agent_settled` [guess on semantics, the event exists in repo code] | `check` on changed files |

Harness-specific failure rule: on Copilot a crashing or exit-2 `preToolUse` hook denies the call [copilot-docs], so the Copilot wrapper path always exits 0 and prints only a deny object or nothing, as `pstack/hooks/pre-tool-use.sh` already does [repo].

## A. Hooks

This table is the Claude Code adapter, the reference behaviour. Other harnesses map onto it through "Harnesses" above.

All hooks run one wrapper, `bash "${CLAUDE_PLUGIN_ROOT}/hooks/guidelines.sh" claude`. The wrapper runs `python3 -I "<plugin root>/skills/principle-code-quality/scripts/guideline_hook.py" --harness <name>` with the payload on stdin. The adapter branches on the event name.

Other harness wiring:

- Codex, `codex-hooks.json`: `SessionStart` (`startup|resume|clear|compact`), `UserPromptSubmit`, `PreToolUse` matcher `apply_patch`, `PostToolUse` matcher `apply_patch`. Each command is `"${CLAUDE_PLUGIN_ROOT}/hooks/guidelines.sh" codex` with a `commandWindows` that runs `py -3 -I ...guideline_hook.py --harness codex`.
- Copilot CLI, `copilot-hooks.json`: `sessionStart`, `preCompact`, `preToolUse` matcher `edit|create`, `postToolUse` matcher `view|edit|create`. Each command is `"${COPILOT_PLUGIN_ROOT}/hooks/guidelines.sh" copilot`, `timeoutSec` 10.
- Pi: `pi/guidelines.ts` registers `tool_call` (gate), `tool_result` (globals and warnings), `before_agent_start` (globals section and prompt keywords), from `pi/index.ts`.

| # | Event | Matcher | Fires when | Inputs used | Metadata read | Emits | FN risk | FP risk |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `SessionStart` | `startup\|resume\|clear\|compact` | Session starts, resumes, clears, or compacts | `source`, `session_id` | All files, to validate. On `compact`, globals for detected languages | `startup`/`resume`/`clear`: nothing, unless a notice (Python too old, invalid guideline file). `compact`: `additionalContext` with globals for the agent's detected languages | Low. Compaction can drop guidance from context, and this re-sends it | Low. Re-sends text the summary may have kept |
| 2 | `UserPromptSubmit` | none | Every prompt, including turns Claude Code starts itself | `prompt`, `session_id` | `languages`, `scope`, `enabled`, `keywords`, `paths`, `exclude` | `additionalContext`, warn only. Globals for languages newly found from file paths in the prompt. Guidelines whose `keywords` match the prompt, when a language context exists | Medium. A prompt that names no file and no keyword gets nothing here. Rows 3 and 4 catch it on first file touch | Low. Keyword hits need a language context, and dedupe limits repeats |
| 3 | `PreToolUse` | `Write\|Edit\|MultiEdit` | Before a file write | `tool_name`, `tool_input`, `cwd`, `agent_id` | All keys | Deny with reason when a `block` guideline's detector finds a hit that this edit adds. Otherwise `additionalContext`: globals for a newly detected language, keyword matches in the new text, missing-tool notices | Medium. Bash file writes skip this hook (see unit 12). A detector over budget is skipped, and a notice says so | Low. Blocks only on new hits from a detector that ran. Pre-existing hits never block |
| 4 | `PostToolUse` | `Read\|Write\|Edit\|MultiEdit` | After a file read or write succeeds | `tool_name`, `tool_input.file_path`, `cwd`, `agent_id` | All keys | `Read`: `additionalContext` with globals for a newly detected language. `Write`/`Edit`/`MultiEdit`: `additionalContext` with warn findings from detectors on the file as written. Never blocks | Low. Read normally comes before Edit, so globals usually arrive before the first edit | Medium. Pre-existing violations in a legacy file produce warnings. Dedupe limits them to one body per guideline |

Events considered and left out:

- `SubagentStart`. It can add context [docs], but the subagent's languages are unknown at start. State keyed by `agent_id` delivers globals on the subagent's first file touch.
- `PreCompact` / `PostCompact`. `SessionStart` with `compact` covers re-delivery and can add context [docs].
- `PostToolBatch`, `PostToolUseFailure`, `FileChanged`. They add no signal the rows above lack.
- `NotebookEdit`. `.ipynb` maps to no language in `languages.toml`. Known gap.
- `Stop`. Optional unit 12, for files written through Bash.

Codex, Copilot CLI, and Pi wiring are in v1 (requirement 7). Their gaps and fallbacks are in "Degradation by harness".

### Output formats

Every emitted text uses these exact shapes. `<path>` is relative to `CLAUDE_PROJECT_DIR` (else `cwd`) when the file is under it, else absolute, always with `/`.

A guideline delivered in full:

```
[<id>] <severity>
<body>
```

A finding with its guideline body (first time in the window):

```
[<id>] <severity>: <tool>:<code> at <path>:<line>
<body>
```

A finding whose guideline was sent recently:

```
[<id>] <severity>: <tool>:<code> at <path>:<line> (guidance sent earlier)
```

A notice:

```
Notice: <text>
```

`additionalContext` text is `Code-quality guidelines (pstack):` on the first line, then the items joined by one blank line, in this order: notices, findings, full guidelines. Within each group, sort by path, line, then id. A guideline whose detector is unavailable is printed with severity `warn (detector unavailable)`. A global `block` guideline with no detector (`cs.typing.no-dynamic`) is printed with severity `block` and never denies.

A deny reason is:

```
Blocked: this edit adds code that breaks a block guideline. Fix it, then retry the edit.
<finding items, block first, then warn, joined by one blank line>
```

Warn findings in the same file go into the deny reason, because `additionalContext` placement on a denied call is not documented [guess]. Items written into a deny reason count as sent.

Text over 9,000 characters is cut at the last whole item that fits. The ids that did not fit stay unsent, so the next trigger delivers them.

JSON shapes, built with `json.dumps`:

- Deny: `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "<reason>"}}` [docs]
- Context: `{"hookSpecificOutput": {"hookEventName": "<event>", "additionalContext": "<text>"}}` [docs for `PreToolUse`. Same nesting for the other events is [guess] based on the `SubagentStart` and `PreToolUse` examples]
- A notice for the user is also put in top-level `"systemMessage"` [docs].
- Nothing to say: no stdout, exit 0.

## B. Frontmatter keys

Existing keys stay as in the lint plan: `id`, `languages`, `scope`, `severity`, `enabled`, `detectors`. Add three optional keys. Syntax stays flat `key: value`, comma lists, stdlib parse.

| Key | Value | Default | Meaning |
| --- | --- | --- | --- |
| `keywords` | Comma list of lowercase words or phrases | empty | A keyword fires the guideline as a warning when it appears as a whole word or phrase in the prompt (rule below), or in the new text of a pending write to a file of the guideline's languages |
| `paths` | Comma list of globs | empty, meaning every file of the guideline's languages | The guideline applies only to files matching at least one glob |
| `exclude` | Comma list of globs | empty | The guideline never applies to a matching file. Its detectors do not run for that file |

Parsing rules:

- The frontmatter is the lines between the first line `---` and the next line `---`. Each line is `key: value`. Split on the first `: `. Strip both sides.
- A comma list splits on `,` and strips each item. Empty items are dropped.
- An unknown key, a missing required key, a duplicate key, or a bad value makes the file invalid. At run time the engine skips an invalid file and emits `Notice: skipped invalid guideline file <name>: <reason>`. The validation test fails on it.
- Glob match: let `rel` be the file path relative to the project root, with `/`. A glob `g` matches when `fnmatch.fnmatchcase(rel, g)` or `fnmatch.fnmatchcase(rel, "*/" + g)` is true. `*` matches across `/` (fnmatch behaviour), so `tests/*` matches `tests/a/b.py` and `pkg/tests/x.py`.
- Keyword match: lowercase the text. A keyword matches when `re.search(r"(?<![a-z0-9_])" + re.escape(kw) + r"(?![a-z0-9_])", text)` is true.
- A prompt keyword hit counts only when one of the guideline's `languages` is in the agent's detected languages, or is detected from a file path in the same prompt. This keeps "flatten the pancake" from firing a Python rule.

No `events` key. The event follows from `scope` and `severity`. Detectors run before and after writes. Globals go out on language detection. Keywords run on prompts and on pending text.

A global built-in exclusion applies before any guideline glob. A file under a directory named `.git`, `node_modules`, `.venv`, `venv`, `site-packages`, `dist`, `build`, `vendor`, or `__pycache__`, or a file ending in `.min.js`, gets no guidelines and no detectors.

Example (`guidelines/py-error-no-assert-in-prod.md`):

```
---
id: py.error.no-assert-in-prod
languages: python
scope: contextual
severity: warn
enabled: true
detectors: ruff:S101
keywords: assert
exclude: tests/*, test_*.py, *_test.py, conftest.py
---
Do not use `assert` for runtime checks in production code; raise an exception instead.
```

`exclude` with test globs also belongs on `all.literal.no-magic-numbers`, `py.logging.no-print` (for `scripts/*` too, open question 5), and `all.function.max-lines`. The implementer adds them while writing the guideline files.

## C. Detector runner contract

### Selecting detectors for one file

1. Resolve the file's language. Lowercase the basename. Find the longest extension in `languages.toml` that the name ends with (`foo.rs.in` gives `rust`, `x.cs.pp` gives `csharp`, `X.PY` gives `python`). No match means no language. Then the hook does nothing for the file.
2. Drop the file if the built-in exclusion matches.
3. Applicable guidelines are those with `enabled: true`, the file's language in `languages`, `paths` matching (or empty), and `exclude` not matching.
4. Group the applicable guidelines' `detectors` by tool. Only these tools run, and each runs with only these codes. A disabled or excluded guideline's codes are never passed to a tool. This enforces requirement 5.

### Runner interface

A runner is one entry in a table in `guideline_hook.py`:

```python
class Runner(NamedTuple):
    tool: str                 # "ruff"
    languages: frozenset[str] # languages it can check
    probe: tuple[str, ...]    # version command; output must match `expect`
    expect: str               # regex on probe stdout, e.g. r"^ruff \d"
    run: Callable[[str, Path, frozenset[str], Path], RunResult]
                              # (content, real_path, codes, project_root)

class Finding(NamedTuple):
    tool: str
    code: str
    line: int

class RunResult(NamedTuple):
    findings: tuple[Finding, ...] | None  # None: tool did not produce a result
    problem: str                          # empty when findings is not None
```

Rules every runner follows:

- Input is the file content as a string plus the real path. A runner never reads the disk copy itself. `PreToolUse` passes the post-edit content, and `PostToolUse` passes the disk content.
- Pass content on stdin when the tool supports it (`ruff --stdin-filename`, `eslint --stdin --stdin-filename`). Otherwise write it to a file with the same basename in a fresh `tempfile.TemporaryDirectory()` (`code_quality.py`) and map reported paths back to the real path.
- Each subprocess call uses `subprocess.run(..., timeout=RUNNER_TIMEOUT_S, capture_output=True, text=True, check=False, stdin=...)`, an argument list, and no shell.
- Selection is explicit and isolated from project config, so results are deterministic. Ruff runs `ruff check --isolated --line-length 80 --select <codes,sorted,comma-joined> --output-format json --stdin-filename <real_path> -`. ESLint runs `eslint --no-config-lookup --stdin --stdin-filename <real_path> -f json --rule '<json of {code: "error"} for each code>'`. `code_quality.py` runs `python3 -I <skill>/scripts/code_quality.py <tmp_path>`.
- Limits that a guideline states but a tool default differs from go into that runner's fixed argument list (example: `--line-length 80`). Shortcut: per-runner constants, upgrade to a frontmatter key only if a user needs per-project limits.
- Parse machine output only (ruff JSON `code` and `location.row`; eslint JSON `messages[].ruleId` and `line`; `code_quality.py` lines `<path>:<line>: <code> ...`). Unknown output shape gives `findings=None, problem="<tool> output was not understood"`.
- A tool's own input error (`code_quality.py` exit 2, a syntax error, eslint `fatal: true`) gives `findings=None, problem="<tool> could not parse <path>"`.

v1 runners: `code_quality` (always available, it ships in the skill), `ruff`, `eslint` (JavaScript core rules only). Every other tool named in `detectors` (`mypy`, `pylint`, `lizard`, `complexipy`, `opengrep`, `semgrep`, `gdlint`, `roslyn`, `stylecop`, `godot`, `tsc`, and eslint plugin rules such as `@typescript-eslint/*` and `sonarjs/*`) has a table entry with `run=None`. It reports `no runner yet`. ESLint on TypeScript needs `@typescript-eslint/parser`, which `--no-config-lookup` cannot load, so TypeScript files report eslint as `needs @typescript-eslint/parser` (open question 3).

### Finding resolution

1. Index: at startup, build `dict[(tool, code), guideline_id]` from enabled guidelines' `detectors`. A tool:code in two guidelines is invalid (validation test).
2. Map each finding by longest prefix. Among index keys for the finding's tool, pick the longest `code` such that `finding.code == code` or `finding.code.startswith(code)`. This supports ruff selector prefixes like `ruff:PTH`. No key means drop the finding (the tool reported a code we did not ask for).
3. Keep only findings whose guideline applies to the file (step 3 of selection).

### New versus pre-existing hits (`PreToolUse` only)

A finding's identity is `(tool, code, stripped text of its source line)`. Run the same detectors on the pre-edit content (the disk file, or empty for a new file). New hits are the multiset difference post minus pre. Only a new hit on a `severity: block` guideline denies. A pre-existing block hit is reported as `warn` by `PostToolUse`. An edit that moves an old violation does not block, because the line text is unchanged.

The pre-edit run doubles detector time. Skip it for a new file. For `Write` to an existing file and for `Edit`, it is required, and it counts against the budget in E.

### Tool missing, wrong, or failed

A tool is available when it is found by `shutil.which`, or as `<project_root>/node_modules/.bin/<tool>` or `<project_root>/.venv/bin/<tool>` (already-installed project tools, no download), and its `probe` stdout matches `expect`. The probe result is cached in session state.

When a needed tool is unavailable, timed out, or returned `findings=None`:

1. Emit once per agent per tool and reason: `Notice: <tool> <reason>, so detectors <tool:code, ...> did not run. Their guidelines follow as warnings.` Reasons are exactly `is not installed`, `is not the expected program`, `has no runner yet`, `timed out after 1.5 s`, `needs @typescript-eslint/parser`, `could not parse <path>`, `output was not understood`. Put the same notice in `systemMessage` so the user sees it.
2. Deliver each affected guideline in full as `warn (detector unavailable)`, subject to dedupe. A `block` guideline never denies through an unavailable detector.
3. Never treat an unavailable detector as a clean pass.

Requirement 6 for detectors: the runner table is the allowed tool list. `guideline-mapping.md` names `sonar:` detectors (`sonar:S138`, `sonar:S104`, and others). Those are SonarQube/SonarCloud rule keys, which run through a Sonar server or hosted service, so they break requirement 6. Drop every `sonar:` detector when writing the guideline files. The same rules stay covered by `eslint:sonarjs/*` (eslint-plugin-sonarjs, an ESLint plugin) and the other tools in each list. The validation test rejects a tool that has no runner table entry.

### Building post-edit content in `PreToolUse`

`path = tool_input.file_path`. Read the current file as UTF-8 if it exists. Then:

- `Write`: post is `tool_input.content`.
- `Edit`: if the file does not exist and `old_string` is empty, post is `new_string` [guess: Edit's create behaviour]. If `replace_all` is true, post is `current.replace(old_string, new_string)`. Otherwise `old_string` must occur exactly once (`current.count(old_string) == 1`) and post is `current.replace(old_string, new_string, 1)`.
- `MultiEdit`: apply each item of `tool_input.edits` in order with the Edit rule [guess: input shape].
- If the file is not valid UTF-8, or `old_string` is missing or not unique, emit nothing. The tool itself refuses the call [docs], so no write happens.

## D. Session state

Location: `<data>/guideline-state/<session_id>/<agent>.json`. `<data>` is `CLAUDE_PLUGIN_DATA` on Claude Code [docs] and on Codex, which also sets it [codex-docs]. On Copilot CLI it is `${COPILOT_HOME:-$HOME/.copilot}/pstack-data` [guess: no documented plugin data dir]. On Pi it is the Pi agent directory plus `/pstack-data` [repo: `settings.agentDir` in `pi/prompt.ts`]. `<agent>` is `main`, or the payload's `agent_id` with characters outside `[A-Za-z0-9_-]` replaced by `_`. If `CLAUDE_PLUGIN_DATA` is unset, use `<tempfile.gettempdir()>/pstack-guideline-state-<uid>/`. Shared probe cache: `<session_id>/tools.json`.

One file per agent keeps concurrent subagents from writing the same file. Writes are atomic (write `<file>.tmp-<pid>`, then `os.replace`). Parallel hook runs inside one agent can still lose an update. The worst case is one guideline sent twice, which is harmless.

Agent file shape:

```json
{
  "prompt": 7,
  "languages": ["python"],
  "sent": {"py.comprehension.one-for": 3},
  "notices": ["ruff:is not installed"],
  "scans": {"<sha256 of content>": [["code_quality", "CQ001", 2]]},
  "pending": ["py.comprehension.one-for"]
}
```

- `prompt` counts `UserPromptSubmit` events. Only `main` has it. Subagents use `0` throughout.
- `sent[id]` is the `prompt` value when the guideline body was last delivered. A guideline is suppressed while `prompt - sent[id] < RESEND_AFTER_PROMPTS` (20). In a subagent, a sent guideline stays suppressed for the subagent's life.
- `languages` grows when a language is first detected. Detection adds the language and delivers its applicable globals in the same call.
- `scans` caches detector results by content hash, at most 20 entries, oldest dropped. `PostToolUse` reuses the `PreToolUse` result when the written content hashes the same.
- Notices dedupe per tool and reason for the agent's life.
- `pending` holds ids picked when the harness had no context channel (see "Degradation by harness"). The next event that can carry context delivers them first, subject to dedupe.

Lifecycle:

- `SessionStart` `startup`: delete `guideline-state/*` directories whose mtime is older than 7 days. This replaces a `SessionEnd` hook.
- `SessionStart` `clear`: delete the `main.json` of this session. The context is empty again.
- `SessionStart` `resume` and `fork`: keep state. The resumed context still holds what was sent. Fork with a new `session_id` starts empty, which re-sends. That is harmless.
- `SessionStart` `compact`: set `sent` to `{}` in `main.json`, keep `languages`, and deliver all applicable globals for `languages` at once. Without this, compaction would drop globals that never come back, because languages are already detected.
- Subagent: its own file starts empty, so its first code-file touch delivers globals into its own context. The parent's `sent` does not suppress anything in a subagent, because the subagent's context never saw it.

## E. Latency budget

| Hook | Config `timeout` | Internal deadline | Work | Over budget |
| --- | --- | --- | --- | --- |
| `SessionStart` | 5 s | 1 s | Parse guidelines, prune state | Skip the prune. Never skip validation notices |
| `UserPromptSubmit` | 5 s | 300 ms | Parse, regex scans of the prompt. No subprocess | Nothing to skip. If parse plus scan exceeds 300 ms, the regression shows in tests |
| `PreToolUse` | 10 s | 2.5 s total | Build content, run detectors twice (pre and post) | Each runner has `RUNNER_TIMEOUT_S = 1.5`. Run `code_quality` first (block guidelines depend on it and it is fastest), then tools with block guidelines, then the rest. Once 2.5 s has passed since start, do not start another runner. Emit `Notice: <tool> timed out after 1.5 s ...` for a timed-out one and `Notice: skipped <tool>, the 2.5 s budget was spent; PostToolUse checks it` for each skipped one |
| `PostToolUse` | 15 s | 5 s | Detectors on disk content, cache first | Same per-runner timeout and ordering. A tool skipped here gets a notice and is not retried |

Expected costs from the [measured] table: Python start 45 ms, `code_quality.py` 40 ms, ruff 227 ms, eslint 145 ms. A Python edit with both runners and the pre-edit run comes to about 0.6 s, inside budget.

Run the engine as one Python process per hook call. Do not start a second Python for `code_quality.py`. Import its `check_source` from the skill's `scripts/` directory instead (same function, no subprocess, no temp file). The runner contract above still describes its output, and the CLI path stays for users.

## F. Failure policy

| Failure | Hook | Policy | Reason |
| --- | --- | --- | --- |
| Copilot `preToolUse` wrapper exits non-zero | Copilot | Never happens: the wrapper always exits 0 | Copilot denies the call on a crash or exit 2 [copilot-docs]. That would be a fail-closed false positive on every write |
| Engine raises an exception | any | Fail open. The wrapper sees a non-zero exit, prints `{"systemMessage": "pstack guideline hook failed; code-quality guidelines were not checked for this call. Details: <CLAUDE_PLUGIN_DATA>/guideline-state/errors.log"}`, appends stderr to that log, and exits 0 | Failing closed would deny every write in the session on one bug. That is a false positive on every edit. The notice turns a silent gap into a known one, which is what requirement 4 asks |
| Python missing or older than 3.11 | `SessionStart` | Fail open with a notice: `Notice: code-quality guideline hooks need Python 3.11 or later; none was found, so no guideline checks run in this session.` In `additionalContext` and `systemMessage` | Without Python nothing can run. Saying so once is the visible gap |
| Python missing or older than 3.11 | other hooks | Silent exit 0 | `SessionStart` already said so. Repeating it on every call is noise |
| Detector missing, wrong program, timed out, parse failure | `PreToolUse`, `PostToolUse` | Fail open to warn delivery (C, "Tool missing") | A gap is worse than noise, so its guidelines are sent as warnings. Blocking on a guess would break requirement 4 |
| Post-edit content cannot be built | `PreToolUse` | Emit nothing | The tool refuses the same call [docs], so nothing is written. `PostToolUse` covers any write that does happen |
| Invalid guideline file | any | Skip the file, emit the notice once per agent | One bad file must not disable the rest |
| State file unreadable or corrupt | any | Treat as empty, overwrite | Worst case is a re-send |
| Malformed payload JSON | any | Exit 0, no output | No file or prompt to check |

No hook fails closed. The only deny is a detector that ran and reported a new hit on a `block` guideline.

## G. Tests

Three test files, matching existing styles. The third is `plugins/pstack/pi/guidelines.test.ts` for the Pi adapter (test 36), run with `bun test`, in the style of `plugins/pstack/skills/poteto-mode/scripts/orch/orch.test.ts` (`bun:test`).

- `plugins/pstack/hooks/tests/guidelines.test.sh` runs the real wrapper as a subprocess, sources `scripts/hook-test-assertions.sh`, and is picked up by `scripts/run-hook-tests.sh`.
- `plugins/pstack/skills/principle-code-quality/scripts/test_guidelines.py` (unittest, subprocess style like `test_code_quality.py`) validates the real guideline files.

Common setup for the hook tests:

- `CLAUDE_PLUGIN_ROOT=plugins/pstack`, `CLAUDE_PLUGIN_DATA=$(mktemp -d)`, a new `session_id` per test, `cwd` and `CLAUDE_PROJECT_DIR` set to a temp project.
- `PSTACK_GUIDELINES_DIR` points at `plugins/pstack/hooks/tests/fixtures/guidelines/` except where a test says "real guidelines". The engine reads that variable, and only tests set it.
- `PATH` is a temp `bin/` with `python3` and stub tools only. Stub `ruff` and `eslint` are shell scripts that append their argv to `$WORK/<tool>.args`, answer the probe (`ruff 0.16.9`, `v10.1.0`), and print canned JSON. This makes output independent of installed tools.

Fixture guidelines (exact files, frontmatter keys then body):

| File | Keys | Body |
| --- | --- | --- |
| `py-comprehension-one-for.md` | `id: py.comprehension.one-for`, `languages: python`, `scope: contextual`, `severity: block`, `enabled: true`, `detectors: code_quality:CQ001`, `keywords: list comprehension, flatten` | ``Use at most one `for` clause per comprehension. Write a flattening comprehension as an explicit `for` loop that names each intermediate value.`` |
| `py-comprehension-no-nested-call.md` | `id: py.comprehension.no-nested-call`, `python`, `contextual`, `warn`, `true`, `code_quality:CQ002` | ``Inside a comprehension, do not pass a call's result straight into another call. Bind the inner result to a name in an explicit `for` loop.`` |
| `py-error-no-assert-in-prod.md` | as the example in B | as the example in B |
| `py-import-no-star.md` | `id: py.import.no-star`, `python`, `contextual`, `block`, `true`, `ruff:F403` | ``Import names explicitly; do not use `from module import *`.`` |
| `py-logging-no-print.md` | `id: py.logging.no-print`, `python`, `contextual`, `warn`, `enabled: false`, `ruff:T201` | `Use the logging module, not print.` |
| `py-data-dataclass-over-dict.md` | `id: py.data.dataclass-over-dict`, `python`, `global`, `warn`, `true`, `detectors:` empty | ``Model a record with a `@dataclass`, not a `dict` with fixed string keys.`` |
| `ts-binding-no-var.md` | `id: ts.binding.no-var`, `languages: typescript, javascript`, `contextual`, `block`, `true`, `eslint:no-var` | ``Declare bindings with `const`, or `let` when reassigned; never `var`.`` |

`PAGES` below is the two-line file `def pages(paths):\n    return tuple(page for path in paths for page in parse_page(_read(path)))\n`.

| # | Behaviour | Input | Expected |
| --- | --- | --- | --- |
| 1 | Motivating case, real guidelines | `PreToolUse` `Write` of `PAGES` to `<project>/pages.py`, real guidelines, stub `ruff` printing `[]` | `permissionDecision` is `deny`. The reason starts with `Blocked: this edit adds code that breaks a block guideline. Fix it, then retry the edit.\n\n[py.comprehension.one-for] block: code_quality:CQ001 at pages.py:2\n` followed by the exact body line of the real `py-comprehension-one-for.md` |
| 2 | Motivating case, exact output | Same, fixture guidelines | Reason equals `Blocked: this edit adds code that breaks a block guideline. Fix it, then retry the edit.\n\n[py.comprehension.one-for] block: code_quality:CQ001 at pages.py:2\nUse at most one ``for`` clause ...value.\n\n[py.comprehension.no-nested-call] warn: code_quality:CQ002 at pages.py:2\nInside a comprehension, ... ``for`` loop.` (bodies verbatim from the fixture table) |
| 3 | Clean write, first Python touch | `PreToolUse` `Write` of the `EXPLICIT_LOOP` text from `test_code_quality.py` to `pages.py` | No deny. `additionalContext` equals `Code-quality guidelines (pstack):\n\n[py.data.dataclass-over-dict] warn\nModel a record with a ``@dataclass``, not a ``dict`` with fixed string keys.` |
| 4 | Second clean write | Test 3 again, same session | Empty stdout, exit 0 |
| 5 | Pre-existing violation does not block | `pages.py` on disk is `PAGES`. `Edit` with `old_string: "def pages(paths):"`, `new_string: "def pages(paths):  # noqa-free"` | No deny. Then `PostToolUse` `Edit` on the same file gives `additionalContext` containing `[py.comprehension.one-for] warn: code_quality:CQ001 at pages.py:2` |
| 6 | Edit that adds the violation blocks | Disk has the explicit loop. `Edit` replaces the loop body with the flattening return | `deny`, reason contains `[py.comprehension.one-for] block: code_quality:CQ001 at pages.py:` |
| 7 | `replace_all` | Disk has two lines `x = 1`. `Edit` `old_string: "x = 1"`, `new_string: "x = [a for b in c for a in b]"`, `replace_all: true` | `deny`, reason has two CQ001 block items, lines 1 and 2 |
| 8 | Edit that the tool would refuse | `old_string` not in the file | Empty stdout, exit 0 |
| 9 | Non-code file | `Write` of `PAGES` to `notes.md` | Empty stdout, exit 0 |
| 10 | `exclude` | `Write` `assert x\n` to `tests/test_app.py`, then to `src/app.py` | `ruff.args` shows `--select F403` for the first and `--select F403,S101` for the second |
| 11 | `enabled: false` | `Write` `print("x")\n` to `src/app.py` | `T201` absent from every `ruff.args` line. Output does not contain `py.logging.no-print` |
| 12 | Missing tool is visible | `PATH` without `ruff`, `Write` `from os import *\n` to `src/app.py` | `additionalContext` contains `Notice: ruff is not installed, so detectors ruff:F403, ruff:S101 did not run. Their guidelines follow as warnings.` and `[py.import.no-star] warn (detector unavailable)`. `systemMessage` contains the same notice. No deny |
| 13 | Wrong program under the tool name | Stub `ruff` prints `Usage: sg group` for the probe | Notice reason `is not the expected program` |
| 14 | Timeout | Stub `ruff` sleeps 5 s | Hook returns in under 3 s. Output contains `Notice: ruff timed out after 1.5 s, so detectors ...` |
| 15 | Missing ESLint on a TypeScript file | `PATH` without `eslint`. `Write` `var x = 1\n` to `a.ts` | Output contains `Notice: eslint is not installed` and `[ts.binding.no-var] warn (detector unavailable)`. No deny |
| 16 | Dedupe window | Main agent. Trigger CQ002 warn, then 19 `UserPromptSubmit`, trigger again, then 1 more prompt, trigger again | Second output has `(guidance sent earlier)`. Third output has the body again |
| 17 | Subagent gets its own delivery | After test 3, a `PostToolUse` `Read` of `pages.py` with `agent_id: "a1"` | `additionalContext` contains `[py.data.dataclass-over-dict] warn` |
| 18 | Compaction re-sends globals | After test 3, `SessionStart` `source: "compact"` | `additionalContext` equals the test 3 text. A following `Read` of `pages.py` gives empty stdout |
| 19 | Prompt keyword with language | `UserPromptSubmit` `prompt: "flatten the lists in parser.py"` | `additionalContext` contains `[py.comprehension.one-for] warn` and `[py.data.dataclass-over-dict] warn` |
| 20 | Prompt keyword without language | New session, `prompt: "flatten the pancake"` | Empty stdout |
| 21 | Language by longest suffix | `PostToolUse` `Read` of `x.cs.pp`, `foo.rs.in`, `X.PY` | Engine debug mode `--language <path>` prints `csharp`, `rust`, `python` |
| 22 | `MultiEdit` sequential | Two edits where the second edit's `old_string` exists only after the first | Content built correctly, `deny` on the CQ001 the second edit adds |
| 23 | Invalid guideline file | Fixture dir plus `bad.md` missing `severity` | Output contains `Notice: skipped invalid guideline file bad.md: missing key severity` |
| 24 | Engine crash | `PSTACK_GUIDELINES_DIR` set to a regular file | Exit 0. stdout is the fixed `systemMessage` JSON from F. `errors.log` is not empty |
| 25 | Python missing | `SessionStart` with `PATH` that has no `python3`, `python`, or `py` | `systemMessage` and `additionalContext` contain the Python notice from F |
| 26 | Wiring, Claude Code | Read `plugins/pstack/hooks/hooks.json` | Four entries as in H, unit 7. Each command is `bash "${CLAUDE_PLUGIN_ROOT}/hooks/guidelines.sh" claude`. Timeouts 5, 5, 10, 15. `guidelines.sh` is executable |
| 27 | Codex gate | Codex `PreToolUse` payload, `tool_input.command` = `*** Begin Patch\n*** Add File: pages.py\n+def pages(paths):\n+    return tuple(page for path in paths for page in parse_page(_read(path)))\n*** End Patch` | `hookSpecificOutput.permissionDecision` is `deny`, reason identical to test 2 |
| 28 | Codex update patch | Disk has the explicit loop. A patch with `*** Update File: pages.py`, an `@@` hunk that swaps the loop for the flattening return | `deny`, reason contains `[py.comprehension.one-for] block: code_quality:CQ001 at pages.py:` |
| 29 | Codex patch that does not apply | Hunk context not in the file | Empty stdout, exit 0 |
| 30 | Copilot gate | Copilot `preToolUse` payload `{"toolName":"create","toolArgs":"{\"path\":\"pages.py\",\"file_text\":\"<PAGES>\"}","sessionId":"s1"}` | stdout is top-level `{"permissionDecision":"deny","permissionDecisionReason":<reason identical to test 2>}` |
| 31 | Copilot globals wait for postToolUse | Copilot `preToolUse` of the clean explicit loop, then `postToolUse` for the same call | `preToolUse` stdout empty. `postToolUse` stdout is `{"additionalContext": <test 3 text>}` |
| 32 | Copilot prompt keywords are queued | `userPromptSubmitted` with `prompt: "flatten the lists in parser.py"`, then `postToolUse` `view` of `parser.py` | First stdout empty. Second `additionalContext` contains `[py.comprehension.one-for] warn` |
| 33 | Copilot compaction | After test 31, `preCompact`, then `postToolUse` `view` of `pages.py` | Second output contains `[py.data.dataclass-over-dict] warn` again |
| 34 | Copilot never exits non-zero | `preToolUse` with `PSTACK_GUIDELINES_DIR` set to a regular file | Exit 0, stdout empty or a JSON object with no `permissionDecision` |
| 35 | Neutral core | `guideline_hook.py --harness neutral` with a `pre_write` event for `PAGES` | `{"deny": <reason identical to test 2>, "context": null, "notice": null}` |
| 36 | Pi adapter | `pi/guidelines.test.ts` calls the `tool_call` handler with `{toolName: "write", input: {path: "pages.py", content: PAGES}}` | Returns `{ block: true, reason: <reason identical to test 2> }` |
| 37 | Skills-only fallback | `python3 guideline_hook.py check pages.py` on a file holding `PAGES`, fixture guidelines | Exit 1. stdout starts with `[py.comprehension.one-for] block: code_quality:CQ001 at pages.py:2` |
| 38 | Wiring, Codex and Copilot | Read `codex-hooks.json` and `copilot-hooks.json` | Entries as in A, "Other harness wiring". `scripts/lint-hook-references.sh` passes |

`test_guidelines.py` checks the real files:

- Every file parses. Keys are a subset of the nine known keys, required keys present, no duplicates.
- `id` values are unique. The file name is the id with `.` replaced by `-`, plus `.md`.
- Every `languages` entry is a section in `languages.toml`. No extension maps to two languages.
- `scope` is `global` or `contextual`. `severity` is `block` or `warn`. `enabled` is `true` or `false`.
- A `contextual` guideline has at least one detector or at least one keyword.
- Each `tool:code` appears in only one guideline.
- Each tool in `detectors` has a runner table entry (`run` may be `None`).
- A `block` guideline that is `contextual` has at least one detector. Keywords alone never block.
- `keywords` are lowercase.
- Body is not empty and is at most 4 lines.
- The body of `py.comprehension.one-for` names `for` and `loop`. This keeps test 1 meaningful.

## H. Implementation plan

Files:

- `plugins/pstack/skills/principle-code-quality/guidelines/<id-with-hyphens>.md`, one per guideline.
- `plugins/pstack/skills/principle-code-quality/scripts/guideline_core.py`, the harness-neutral core: guideline parsing, index, language lookup, globs, keywords, runners, state, `NeutralEvent` to `NeutralResult`. Stdlib only, at most 600 lines. Imports `check_source` from `code_quality.py` in the same directory.
- `plugins/pstack/skills/principle-code-quality/scripts/guideline_hook.py`, the adapters (`--harness claude|codex|copilot|neutral`), the apply_patch applier, and the `check` CLI. Stdlib only, at most 600 lines.
- `plugins/pstack/pi/guidelines.ts`, the Pi adapter, registered from `plugins/pstack/pi/index.ts`, with a Node test beside it.
- `plugins/pstack/hooks/codex-hooks.json` and `plugins/pstack/hooks/copilot-hooks.json`, with entries added next to the existing ones.
- A short section in `plugins/pstack/skills/principle-code-quality/SKILL.md` for harnesses with no hooks.
- `plugins/pstack/skills/principle-code-quality/scripts/test_guidelines.py`.
- `plugins/pstack/hooks/guidelines.sh`, the wrapper for Claude Code, Codex, and Copilot. It takes the harness name as its first argument, finds `python3`, then `python`, then `py -3`, checks `sys.version_info >= (3, 11)`, runs the engine, and applies the F crash policy.
- `plugins/pstack/hooks/hooks.json`, with the new entries added next to the existing `SessionStart` entry.
- `plugins/pstack/hooks/tests/guidelines.test.sh` and `plugins/pstack/hooks/tests/fixtures/guidelines/*.md`.

Units, each ending in a check, in order. Unit 12 is optional.

1. **Confirm the guesses.** On each harness (Claude Code, Codex, Copilot CLI, Pi), log raw hook payloads for a file write, a file edit, a read, a prompt, compaction, and one subagent tool call. On Claude Code log for `Edit`, `Write`, `PostToolUse` of each, `SessionStart` `compact`, and one subagent tool call. Confirm `agent_id` presence, Edit's create behaviour, `UserPromptSubmit` inside subagents, and that `hookSpecificOutput.additionalContext` works for `UserPromptSubmit`, `PostToolUse`, and `SessionStart`. Also confirm the Copilot `edit`/`create` arg names, whether Codex `PostToolUse` fires for `apply_patch`, the Pi `edit` input fields and whether `before_agent_start` carries the prompt, and how each harness identifies a subagent. Update this file's `[guess]` labels. Check: payload logs saved under `.ai/`.
2. **Guideline files and validation.** Write all files from `guideline-mapping.md` with the B keys. Write `test_guidelines.py`. Check: `python3 -m unittest` in `scripts/` passes, and a deliberately broken copy fails with the expected message.
3. **Parse, index, language.** In `guideline_core.py`: frontmatter parser, index, `languages.toml` lookup, globs, keyword matcher, `--language <path>` debug mode. Check: tests 21 and 23.
4. **State, neutral interface, global delivery.** `NeutralEvent`/`NeutralResult`, the `--harness neutral` and `--harness claude` adapters, state file, dedupe, `pending`, `UserPromptSubmit` and `PostToolUse` `Read`. Check: tests 16 to 20 and 35.
5. **PreToolUse gate with `code_quality`.** Post-edit content, pre and post runs, new-hit diff, deny output. Check: tests 1 to 9 and 22.
6. **ruff and eslint runners.** Probe, missing-tool notice, timeout, budget. Check: tests 10 to 15.
7. **PostToolUse advice, SessionStart, wiring, wrapper.** Add to `plugins/pstack/hooks/hooks.json`: `SessionStart` matcher `startup|resume|clear|compact` timeout 5 (a second hook in the existing entry), `UserPromptSubmit` no matcher timeout 5, `PreToolUse` matcher `Write|Edit|MultiEdit` timeout 10, `PostToolUse` matcher `Read|Write|Edit|MultiEdit` timeout 15. Check: tests 3, 5, 17, 18, 24, 25, 26, and `scripts/run-hook-tests.sh` passes.
8. **Codex adapter.** Payload mapping, in-memory apply_patch applier (Add, Update with `@@` hunks, Delete, Move), `codex-hooks.json` entries. Check: tests 27 to 29 and 38.
9. **Copilot adapter.** Payload mapping (`toolArgs` is a JSON string), `pending` queue, `preCompact`, always-exit-0 wrapper path, `copilot-hooks.json` entries. Check: tests 30 to 34 and 38.
10. **Pi adapter.** `pi/guidelines.ts` and its registration. Check: test 36, and one manual Pi session writing `PAGES` is blocked.
11. **Skills-only fallback.** The `check` CLI and the SKILL.md section: "If your harness ran no guideline hook this session, run `python3 <skill dir>/scripts/guideline_hook.py check <files you changed>` after each edit, fix every `block` line before continuing, and follow the printed guidelines." Check: test 37.
12. **Optional, after the user answers open question 7: Stop hook for Bash writes.** On `Stop`, list files changed since the turn's `UserPromptSubmit` (mtime newer than a stamp written there), skip ones whose content hash is in `scans`, run detectors, and block stopping only on new `block` hits compared with `git show HEAD:<path>`. Respect `stop_hook_active` to avoid loops. Check: a Bash `cat > x.py` with a CQ001 line makes Stop block once.

## I. Open questions for the user

1. **Placement.** `scripts/generate-plugin-manifests.py` calls pstack "the unmodified michael-denyer/pstack-claude plugin", yet `code_quality.py` and `languages.toml` already live there. Should the hooks go in pstack as this spec says, or in a separate dotai plugin?
2. **`enabled: false` lost on update.** Plugin updates replace the files. Do you want a user override file in the per-harness data directory from D (it survives updates), for example one line `py.logging.no-print: false` per guideline?
3. **TypeScript ESLint.** Use the project's own ESLint config (needs it to enable our rules) or isolated core rules only (TypeScript files then get warn-only delivery)?
4. **Cursor hooks.** dotai ships Cursor skills only, through skills.sh. Cursor has a hooks system of its own [guess: not checked]. Should dotai add Cursor wiring later, or is the `check` CLI fallback enough there and on opencode, Hermes, and Gemini CLI?
5. **Resend window and test excludes.** Is 20 prompts right? Which guidelines skip tests and `scripts/`?
6. **Python 3.11 or later.** Other hooks here need only bash and awk. Is a Python requirement acceptable for this one?
7. **Bash-written files and no-detector guidelines.** Add the optional Stop command hook (unit 12)? Separately, add a Stop `agent` hook that judges changed files against global guidelines, warn-only, at up to 60 s per stop?
8. **Vectors.** Left out by your instruction. Revisit later if keyword matching misses too much.
