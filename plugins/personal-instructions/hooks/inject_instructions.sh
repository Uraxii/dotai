#!/usr/bin/env bash
# Inject one of the plugin's instruction files into a session.
#
# --file picks the file. instructions.md is wired to session start and
# subagent start. main-agent-instructions.md is wired to session start only,
# so fresh subagents do not get it. Forked subagents (Claude Code forks, Codex
# fork_context or multi_agent_v2 forks) inherit it from the parent's history,
# and no hook can prevent that.
#
# Root session hook text does not reach subagents, so each harness wires both
# a session-start and a subagent-start hook to this script. Subagents are
# covered only where the harness fires a subagent-start hook. Known gaps:
# Copilot's built-in general-purpose agent fires no subagentStart; Copilot has
# no documented re-inject after compaction; Codex subagents get nothing after
# compaction.
# - claude SessionStart: plain text. Claude ignores plain stdout on
#   SubagentStart, so that event gets the hookSpecificOutput JSON line.
# - codex: one hookSpecificOutput JSON line, hookEventName set to --event.
# - copilot: one {"additionalContext": ...} JSON line.
# A missing or empty file prints nothing and exits 0. Any other error prints
# nothing on stdout, one line on stderr, and exits 0.
#
# It needs only bash and awk; inject_instructions.awk writes the output.
# Windows runs it with Git Bash: Claude Code directly, and Codex and Copilot
# through run-hook.cmd.

fail() {
  echo "inject_instructions: $1" >&2
  exit 0
}

harness=
event=SessionStart
file=instructions.md
while [ $# -gt 0 ]; do
  [ $# -ge 2 ] || fail "error: argument $1: expected one argument"
  case "$1" in
    --harness)
      case "$2" in claude | codex | copilot) harness=$2 ;; *) fail "error: argument --harness: invalid choice: '$2' (choose from 'claude', 'codex', 'copilot')" ;; esac
      ;;
    --event)
      case "$2" in SessionStart | SubagentStart) event=$2 ;; *) fail "error: argument --event: invalid choice: '$2' (choose from 'SessionStart', 'SubagentStart')" ;; esac
      ;;
    --file)
      case "$2" in instructions.md | main-agent-instructions.md) file=$2 ;; *) fail "error: argument --file: invalid choice: '$2' (choose from 'instructions.md', 'main-agent-instructions.md')" ;; esac
      ;;
    *) fail "error: unrecognized arguments: $1" ;;
  esac
  shift 2
done
[ -n "$harness" ] || fail "error: the following arguments are required: --harness"

plugin_root=$(cd -P "$(dirname "${BASH_SOURCE[0]}")/.." && pwd) || fail "cannot find the plugin root"
path="$plugin_root/$file"
[ -f "$path" ] || exit 0
FILE=$path HARNESS=$harness EVENT=$event LC_ALL=C \
  awk -f "$plugin_root/hooks/hook-json.awk" -f "$plugin_root/hooks/inject_instructions.awk"
case $? in
  0) ;;
  3) fail "UnicodeDecodeError: $path is not valid UTF-8" ;;
  *) fail "cannot read $path" ;;
esac
exit 0
