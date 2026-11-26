#!/bin/bash
# Runs the code-quality guideline engine for one hook call. The harness name
# is the first argument (claude or codex) and the hook payload is on stdin.
# Every path exits 0: a failure here must never block the user's work. A
# failure is never silent either: the user gets a systemMessage, and the
# engine's stderr goes to guideline-state/errors.log in the data directory.
# Needs Python 3.11 or later; without it SessionStart says so once.

harness=${1:-}
hooks_dir=${BASH_SOURCE[0]%[/\\]*}
[ "$hooks_dir" = "${BASH_SOURCE[0]}" ] && hooks_dir=.
engine="$hooks_dir/../skills/principle-code-quality/scripts/guideline_hook.py"
input=$(cat)

json_text() {
  local text=${1//\\/\\\\}
  printf '%s' "${text//\"/\\\"}"
}

python=()
for candidate in python3 python "py -3"; do
  # shellcheck disable=SC2086
  if $candidate -I -c 'import sys; sys.exit(sys.version_info < (3, 11))' 2>/dev/null; then
    read -ra python <<<"$candidate"
    break
  fi
done
if [ "${#python[@]}" -eq 0 ]; then
  session_start='"hook_event_name"[[:space:]]*:[[:space:]]*"SessionStart"'
  if [[ "$input" =~ $session_start ]]; then
    notice='Notice: code-quality guideline hooks need Python 3.11 or later; none was found, so no guideline checks run in this session.'
    printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"},"systemMessage":"%s"}\n' "$notice" "$notice"
  fi
  exit 0
fi

data=${CLAUDE_PLUGIN_DATA:-${PLUGIN_DATA:-}}
if [ -n "$data" ]; then
  export PSTACK_GUIDELINE_DATA="$data"
else
  data="${TMPDIR:-/tmp}/pstack-guideline-state-$UID"
fi

# stdout goes straight to the harness; only stderr is captured.
exec 3>&1
errors=$(printf '%s' "$input" | "${python[@]}" -I "$engine" --harness "$harness" 2>&1 >&3)
status=$?
exec 3>&-
[ "$status" -eq 0 ] && exit 0

log="$data/guideline-state/errors.log"
details=''
(
  umask 077
  mkdir -p "$data/guideline-state" || exit
  # Write only in directories this user owns, and never through a symlink.
  for owned in "$data" "$data/guideline-state"; do
    [ -O "$owned" ] && [ ! -L "$owned" ] || exit
  done
  [ -L "$log" ] && exit
  [ -f "$log" ] && [ "$(wc -c <"$log")" -gt 200000 ] && : >"$log"
  printf '%s %s exit %s\n%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$harness" "$status" "$errors" >>"$log"
) 2>/dev/null && details=" Details: $(json_text "$log")"
printf '{"systemMessage":"pstack guideline hook failed; code-quality guidelines were not checked for this call.%s"}\n' "$details"
exit 0
