# Context-pressure hook

The dotai plugin installs `hooks/handoff-token-flag.py` for Claude Code,
Codex, and Copilot CLI. Claude Code and Codex run it on `UserPromptSubmit`.
Copilot CLI runs it on `agentStop`, then requests one continuation so the
agent can offer a handoff. The per-session band file prevents a loop.

OpenCode and Hermes install dotai as skills, not as this plugin. Their install
paths do not carry the hook. Do not claim support until each integration has a
repeating event, an external usage signal, and a verified context-injection
path.

An agent cannot measure its own context size. The measurement comes from
outside the conversation, which is why this is a hook and not an instruction.

## Contract

A conforming hook meets all six points. The harness picks the mechanism.

1. **Runs on a repeating per-turn event.** Bind it to something the harness
   fires on every turn, before the agent composes its next reply. A
   session-start event cannot work, because context grows after it fires.
2. **Reads a usage signal from outside the model.** Anything that tracks how
   full the context is: a token count the harness hands the hook, a session
   transcript on disk, a usage field in an API response. Record which signal
   you chose and where it comes from.
3. **Compares the signal against a threshold** set below the point where the
   context degrades or auto-compaction starts, so a handoff can still be
   written with the detail intact.
4. **Fires once per crossing, not once per turn.** Keep per-session state
   outside the conversation, such as a file keyed by session id, and emit
   only when the signal enters a band it has not reported yet. A hook that
   repeats every turn gets ignored, which is the same as not having one.
5. **Emits to the agent, not to the user.** The text goes into the agent's
   context and tells it to offer a handoff at the next natural stopping
   point, name the `handoff` skill, and start no major new work. Follow that
   skill's location rules for the file it writes.
6. **Fails silent.** No signal, unreadable state, or any error means emit
   nothing and exit successfully. A token-count nudge must never break a
   session.

## Find out what your harness offers

Check. Do not assume, and do not copy another harness's answer.

1. Read the harness's hook or event documentation. List the events that fire
   every turn and the data each one receives.
2. Install a hook that only records its own input, take one turn, and read
   what it recorded. Documentation is often behind the runtime.
3. Look for usage numbers in what the hook can reach: its input, a
   transcript or log file it can open, an API response it can inspect.

If no event repeats per turn, or nothing reachable carries usage data, stop
and say so. Do not install a hook that cannot measure anything.

## Verify it fires

An unverified hook is the failure mode this file exists to prevent. Run all
four steps.

1. Feed the hook the input you recorded above and confirm it prints the
   message it should.
2. Set the threshold to zero, take one turn in a live session, and ask the
   agent to quote any text injected into its context that turn. Nothing
   quoted means the hook is not wired in, whatever step 1 printed.
3. Take another turn below the next band. Confirm the hook stays silent.
4. Restore the real threshold. Confirm a fresh session below it stays silent
   and does not error.

## Installed harnesses

Claude Code:

- Event: `UserPromptSubmit`, registered in the plugin's `hooks/hooks.json`, which fires
  before each user turn reaches the agent.
- Input: a JSON envelope on stdin carrying `transcript_path` and
  `session_id`.
- Signal: the last `message.usage` entry in the transcript, summing
  `input_tokens`, `cache_read_input_tokens`, and
  `cache_creation_input_tokens`.
- Threshold and bands: report first past 200k tokens, then once per further
  50k.
- Per-session state: a file in the OS temp directory named by `session_id`,
  holding the last band reported.
- Emission: anything printed to stdout enters the agent's context that turn.
- Fail-safe: always exit 0 and print nothing on error.

Codex uses the same event and snake-case envelope. The hook reads the latest
`event_msg.payload.info.last_token_usage.input_tokens` value from the rollout
transcript. Codex requires the user to review and trust a new or changed
plugin hook before it runs.

Copilot CLI runs the hook at `agentStop`, the repeating event that includes
`transcriptPath`. If the transcript contains no recognized usage record, the
hook estimates context from its UTF-8 byte size. At a new band, it returns a
single `decision: block` response whose reason asks the agent to offer a
handoff. A repeated stop in the same band returns no decision.

Another harness may expose a different event, hand over a token count
directly, or expose no usage data at all. Check yours.
