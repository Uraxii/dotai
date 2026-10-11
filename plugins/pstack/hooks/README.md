# Codex watcher command guard

The hook requires a POSIX shell, `cat`, `grep`, GNU `timeout`, and Python 3 on `PATH`.
The registration reads the top-level `agent_type` field before it starts Python.
Other callers return exit code 0 without output and do not load the guard.

For a watcher, the registration gives the guard five seconds to finish.
GNU `timeout` kills the guard one second after a termination request if needed.
Any nonzero result becomes exit code 2, which blocks the tool call.
This covers a missing Python executable, a missing guard, an import error,
a crash, and a stalled guard.
The ten-second hook timeout leaves time for that blocking result.

The registration does not set `onFailure: "block"` for the whole session.
That setting would also block other callers if the shared hook failed.
Caller selection uses `grep -E` on the raw input.
No match returns exit code 0. A selector error returns exit code 2.
The shell checks JSON token depth to exclude fields inside tool arguments.
A missing shell script also returns exit code 2.

See the Claude Code [input fields](https://code.claude.com/docs/en/hooks#common-input-fields),
[exit code 2](https://code.claude.com/docs/en/hooks#exit-code-2), and
[timeouts](https://code.claude.com/docs/en/hooks#timeouts).
