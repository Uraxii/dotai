#!/usr/bin/env bash
# Emit one SessionStart or SubagentStart context for Claude Code or Copilot CLI.
#
# `codebase-memory-mcp install` gives a harness a global instruction file and
# a lifecycle hook that runs `codebase-memory-mcp hook-augment`. A plugin
# cannot write the instruction file, and two hooks on one event inject two
# contexts. This hook joins instructions.md with hook-augment's graph context,
# so each event injects one context into the session and into every subagent.
#
# On SessionStart it also runs `codebase-memory-mcp config get auto_index`,
# alongside hook-augment, and appends a reminder for the agent to pass on to
# the user when the setting is off. It never changes the setting.
#
# The hook always exits 0 and prints nothing it cannot build.
#
# It needs only bash and awk; lifecycle_context.awk reads and writes the JSON.
# Windows runs it with Git Bash: Claude Code directly, and Copilot through
# run-hook.cmd.

# Deadlines in tenths of a second, under the harnesses' 5 s hook timeout.
AUGMENT_TIMEOUT_TICKS=40
HOOK_BUDGET_TICKS=43
AUTO_INDEX_REMINDER='codebase-memory auto-indexing is off, so new checkouts and worktrees have no graph until indexed. Mention this to the user once, and suggest they run `codebase-memory-mcp config set auto_index true`. Do not run it yourself.'

fail() {
  echo "lifecycle_context: $1" >&2
  exit 0
}

harness=
event=
while [ $# -gt 0 ]; do
  [ $# -ge 2 ] || fail "error: argument $1: expected one argument"
  case "$1" in
    --harness)
      case "$2" in claude | copilot) harness=$2 ;; *) fail "error: argument --harness: invalid choice: '$2' (choose from 'claude', 'copilot')" ;; esac
      ;;
    --event)
      case "$2" in SessionStart | SubagentStart) event=$2 ;; *) fail "error: argument --event: invalid choice: '$2' (choose from 'SessionStart', 'SubagentStart')" ;; esac
      ;;
    *) fail "error: unrecognized arguments: $1" ;;
  esac
  shift 2
done
[ -n "$harness" ] && [ -n "$event" ] || fail "error: the following arguments are required: --harness, --event"

hooks_dir=$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd) || fail "cannot find the hooks directory"
instructions="$hooks_dir/instructions.md"
[ -f "$instructions" ] || fail "FileNotFoundError: $instructions"

work=$(mktemp -d) || fail "cannot create a temporary directory"
trap 'rm -rf "$work"' EXIT
cat >"$work/input"
: >"$work/augment"
: >"$work/config"

ticks=0
# Waits for a child until the shared tick count reaches a deadline, and
# returns the child's exit status. A child still running then is killed and
# timed_out is set.
wait_until() {
  timed_out=
  while kill -0 "$1" 2>/dev/null; do
    if ((ticks >= $2)); then
      kill "$1" 2>/dev/null
      wait "$1" 2>/dev/null
      timed_out=1
      return 1
    fi
    sleep 0.1
    ticks=$((ticks + 1))
  done
  wait "$1"
}

if [ "$event" = SessionStart ]; then
  codebase-memory-mcp config get auto_index </dev/null >"$work/config" 2>/dev/null &
  config_pid=$!
fi

if [ "$harness" = copilot ]; then
  codebase-memory-mcp hook-augment --event "$event" --dialect copilot <"$work/input" >"$work/augment" 2>/dev/null &
else
  codebase-memory-mcp hook-augment <"$work/input" >"$work/augment" 2>/dev/null &
fi
wait_until $! "$AUGMENT_TIMEOUT_TICKS"
[ -z "$timed_out" ] || : >"$work/augment"

reminder=
if [ -n "${config_pid-}" ] && wait_until "$config_pid" "$HOOK_BUDGET_TICKS"; then
  setting=$(<"$work/config")
  setting="${setting#"${setting%%[![:space:]]*}"}"
  setting="${setting%"${setting##*[![:space:]]}"}"
  [ "$setting" = false ] && reminder=$AUTO_INDEX_REMINDER
fi

HARNESS=$harness EVENT=$event REMINDER=$reminder INSTRUCTIONS=$instructions AUGMENT=$work/augment \
  LC_ALL=C awk -f "$hooks_dir/hook-json.awk" -f "$hooks_dir/lifecycle_context.awk" || fail "cannot build the context"
exit 0
