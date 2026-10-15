#!/usr/bin/env bash
# opus_5_reduce_output: Stop hook asking for a plain-English recap of the turn.
#
# Wired in the plugin's hooks/claude-hooks.json under Stop. It needs only
# bash and awk, so Git Bash runs it on Windows. opus_5_reduce_output.awk reads
# the JSON.
# CLEAN_RECAP_* and clean-recap.log retain their original names deliberately.
#
# Env vars, all optional:
# - CLEAN_RECAP_LOG: path to the audit log. Default ~/.claude/clean-recap.log.
# - CLEAN_RECAP_LOG_MAX_BYTES: size at which the log rolls over. Default 1000000.
# - CLEAN_RECAP_MODEL_PATTERN: POSIX extended regex, matched ignoring case, that
#   the current model must match to trigger
#   a recap. Default "opus-5|fable".
#
# Fires when Claude tries to end its turn. Prints {"decision": "block"}, which
# does not stop at all: it hands Claude one more instruction, to write a short
# recap for someone who has not read the code. Three gates decide, in order:
# the loop guard below, the model that answered matching opus-5|fable, and the
# turn having changed something. A turn that mutated nothing has nothing to
# recap, so it is allowed to end silently. Every invocation appends one line
# to an audit log so a declined gate never looks like a hook that never ran.
#
# Hook protocol (Claude Code):
# - stdin: JSON envelope with stop_hook_active, transcript_path.
# - stdout: {"decision": "block", "reason": ...} blocks the stop and feeds
#   reason back as Claude's next instruction; print nothing to let the turn end.
# - exit code: always 0. Any error, missing data or declined gate prints
#   nothing. Never crash the session.
#
# LOOP GUARD: do not remove. Blocking the stop means Claude works on and hits
# Stop again, with stop_hook_active set on that second pass. Ignore it and the
# session can never end.

# The audit log rolls over once, with no numbered backups: it is an audit
# trail for the current stretch of sessions, not a record kept across
# rollovers.
DEFAULT_LOG_MAX_BYTES=1000000
DEFAULT_MODEL_PATTERN='opus-5|fable'

# A prompt, not config. Keep it short; it is injected on every turn.
RECAP_INSTRUCTION='Write a plain recap in a few sentences about what changed and why it matters. Do not write a report, headers, or structured output. The reader has not seen the code, so use no paths, identifiers, line numbers, or code blocks. Leave out caveats and next steps unless something is broken or unfinished.'

hooks_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd) || exit 0
read_json() {
  LC_ALL=C MODE=$1 awk -f "$hooks_dir/hook-json.awk" -f "$hooks_dir/opus_5_reduce_output.awk" "${@:2}"
}

# Appends one audit line. Once the file reaches the size limit, this write
# truncates it instead, so the log never grows without bound. Logging never
# breaks the hook.
log() {
  local path="${CLEAN_RECAP_LOG:-$HOME/.claude/clean-recap.log}"
  local max_bytes="${CLEAN_RECAP_LOG_MAX_BYTES:-$DEFAULT_LOG_MAX_BYTES}"
  max_bytes="${max_bytes#"${max_bytes%%[![:space:]]*}"}"
  max_bytes="${max_bytes%"${max_bytes##*[![:space:]]}"}"
  [[ "$max_bytes" =~ ^[+-]?[0-9]+$ ]] || max_bytes=$DEFAULT_LOG_MAX_BYTES
  local limit=$((10#${max_bytes#[+-]})) stamp size
  [[ "$max_bytes" == -* ]] && limit=$((-limit))
  stamp=$(date +%Y-%m-%dT%H:%M:%S)
  if [ -f "$path" ] && size=$(wc -c <"$path") && ((size >= limit)); then
    printf '%s clean-recap.log rolled over; earlier lines were dropped\n%s %s\n' "$stamp" "$stamp" "$1" >"$path"
  else
    printf '%s %s\n' "$stamp" "$1" >>"$path"
  fi
} 2>/dev/null

# Python repr of a string, which the audit log has always used for patterns.
quote_pattern() {
  local text="${1//\\/\\\\}"
  if [[ "$text" == *"'"* && "$text" != *'"'* ]]; then
    printf '"%s"' "$text"
  else
    printf "'%s'" "${text//\'/\\\'}"
  fi
}

payload_fields=$(read_json payload 2>/dev/null <<<"$(cat)")
payload_status=$?
[ "$payload_status" = 1 ] && exit 0
stop_hook_active=${payload_fields%%$'\n'*}

if [ "$stop_hook_active" = 1 ]; then
  log "fired  stop_hook_active=true -> stand down (recap already written)"
  exit 0
fi
[ "$payload_status" = 0 ] || exit 0

transcript=${payload_fields#*$'\n'}
if [ -z "$transcript" ] || [ ! -f "$transcript" ]; then
  log "fired  no readable transcript_path -> allow"
  exit 0
fi

turn_fields=$(read_json transcript "$transcript" 2>/dev/null) || exit 0
model=${turn_fields%%$'\n'*}
turn=${turn_fields#*$'\n'}

# CLEAN_RECAP_MODEL_PATTERN is a POSIX extended regex, matched ignoring case.
pattern="${CLEAN_RECAP_MODEL_PATTERN:-$DEFAULT_MODEL_PATTERN}"
shopt -s nocasematch
[[ "$model" =~ $pattern ]] 2>/dev/null
matched=$?
if [ "$matched" = 2 ]; then
  log "fired  CLEAN_RECAP_MODEL_PATTERN $(quote_pattern "$pattern") rejected (not a valid extended regular expression) -> using default $(quote_pattern "$DEFAULT_MODEL_PATTERN")"
  pattern=$DEFAULT_MODEL_PATTERN
  [[ "$model" =~ $pattern ]] 2>/dev/null
  matched=$?
fi
shopt -u nocasematch

if [ "$matched" != 0 ]; then
  log "fired  model=$model -> allow (model does not match '$pattern')"
  exit 0
fi

case "$turn" in
  unknown) log "fired  model=$model -> BLOCK (requesting recap; no user prompt found, turn boundary unknown)" ;;
  clean)
    log "fired  model=$model -> allow (turn used no mutating tool, nothing to recap)"
    exit 0
    ;;
  *) log "fired  model=$model -> BLOCK (requesting recap)" ;;
esac

printf '{"decision": "block", "reason": "%s"}\n' "$RECAP_INSTRUCTION"
exit 0
