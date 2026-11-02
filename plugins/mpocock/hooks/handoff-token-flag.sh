#!/usr/bin/env bash
# Flag Claude and Codex context pressure before either harness compacts.
#
# Copilot is not wired because its hook API has no documented token count.
#
# This file is the only copy. Every harness reaches it through a plugin
# manifest in this repository, so a per-machine copy under a user's home
# directory is a fork waiting to happen, not an install step.
#
# Reads the session transcript path from stdin JSON, takes the last recorded
# usage input and cache token counts as a proxy for current context size, and
# injects an instruction the first time that size crosses the 200k soft limit
# (and again every +50k band after, so the nag does not repeat every turn
# within the same band). The agent cannot measure its own context size, so
# this hook measures it from the transcript.
#
# Hook protocol:
# - stdin: a Claude or Codex transcript JSON envelope.
# - stdout: text injected into the current turn.
# - exit code: 0. Any error or missing data prints nothing. Never crash the
#   session.
#
# It needs only bash and awk; handoff-token-flag.awk reads the JSON. Windows
# runs it with Git Bash: Claude Code directly, and Codex through run-hook.cmd.

THRESHOLD=200000
BAND=50000

while [ $# -gt 0 ]; do
  case "$1 ${2-}" in
    "--mode context") shift 2 ;;
    *)
      echo "handoff-token-flag: error: unrecognized arguments: $*" >&2
      exit 2
      ;;
  esac
done

hooks_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd) || exit 0
read_json() {
  LC_ALL=C MODE=$1 awk -f "$hooks_dir/hook-json.awk" -f "$hooks_dir/handoff-token-flag.awk" "${@:2}" 2>/dev/null
}

fields=$(read_json payload <<<"$(cat)") || exit 0
transcript=${fields%$'\n'*}
session_id=${fields##*$'\n'}
[ -f "$transcript" ] || exit 0

tokens=$(read_json transcript "$transcript") || exit 0
[[ "$tokens" =~ ^[0-9]+$ ]] || exit 0
((tokens >= THRESHOLD)) || exit 0

band=$(((tokens - THRESHOLD) / BAND))
state_directory=/tmp
for candidate in "${TMPDIR-}" "${TEMP-}" "${TMP-}"; do
  if [ -n "$candidate" ] && [ -d "$candidate" ]; then
    state_directory=${candidate%/}
    break
  fi
done
safe_id=$(LC_ALL=C tr -cd 'A-Za-z0-9_-' <<<"$session_id")
state_file="$state_directory/dotai-handoff-flag-${safe_id:-unknown}.txt"

last_band=-1
if [ -f "$state_file" ]; then
  recorded=$(tr -d ' \t\r\n' <"$state_file")
  [[ "$recorded" =~ ^([+-]?)([0-9]+)$ ]] && last_band=$((${BASH_REMATCH[1]}10#${BASH_REMATCH[2]}))
fi
((band > last_band)) || exit 0
printf '%s' "$band" >"$state_file" || exit 0

# Python's round(): halves go to the even neighbour.
k=$((tokens / 1000))
remainder=$((tokens % 1000))
if ((remainder > 500 || (remainder == 500 && k % 2 == 1))); then
  k=$((k + 1))
fi
echo "[handoff-token-flag] Main session context ~${k}k tokens, past the 200k soft limit. At the next natural stopping point, suggest writing a handoff doc via the \`handoff\` skill and closing this session; if the user agrees, report the resulting path as the first line. Do not start major new work. Do not silently rely on auto-compact."
exit 0
