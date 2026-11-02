#!/bin/bash
# Behavior tests for handoff-token-flag. 

HOOKS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLUGIN_ROOT_DIR="$(dirname "$HOOKS_DIR")"
# shellcheck source=../../../../scripts/hook-test-assertions.sh
. "$PLUGIN_ROOT_DIR/../../scripts/hook-test-assertions.sh"

HOOK="$HOOKS_DIR/handoff-token-flag.sh"
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
# The band state lives in the temp directory, so each test gets its own.
export TMPDIR="$WORK/state"
mkdir "$TMPDIR"

claude_usage() {
  jq -cn --argjson i "$1" --argjson r "$2" --argjson c "$3" \
    '{message: {usage: {input_tokens: $i, cache_read_input_tokens: $r, cache_creation_input_tokens: $c}}}'
}
codex_usage() {
  jq -cn --argjson i "$1" '{type: "event_msg", payload: {type: "token_count", info: {last_token_usage: {input_tokens: $i, cached_input_tokens: 150000}}}}'
}
# flag SESSION TRANSCRIPT_LINES [ARG...]: runs the hook on a fresh transcript.
flag() {
  local session="$1" lines="$2" transcript
  shift 2
  transcript=$(mktemp "$WORK/transcript.XXXXXX")
  printf '%s\n' "$lines" >"$transcript"
  run_hook "$HOOK" "$@" <<<"$(jq -cn --arg t "$transcript" --arg s "$session" '{transcript_path: $t, session_id: $s}')"
}
message_for() {
  printf '%s\n' "[handoff-token-flag] Main session context ~${1}k tokens, past the 200k soft limit. At the next natural stopping point, suggest writing a handoff doc via the \`handoff\` skill and closing this session; if the user agrees, report the resulting path as the first line. Do not start major new work. Do not silently rely on auto-compact."
}

expect_equal "codex manifest points at codex-hooks.json" ./hooks/codex-hooks.json \
  "$(jq -r .hooks "$PLUGIN_ROOT_DIR/.codex-plugin/plugin.json")"
expect_equal "no Copilot hooks file" absent "$([ -e "$PLUGIN_ROOT_DIR/hooks.json" ] && echo present || echo absent)"

flag session-1 "$(claude_usage 100000 90000 20000)" --mode context
expect_equal "reads Claude usage as input plus both cache counts" "$(message_for 210)"$'\n' "$STDOUT"
expect_equal "exits 0 after a nudge" 0 "$STATUS"

flag session-codex "$(codex_usage 210000)"
expect_equal "reads Codex usage without double counting cache" "$(message_for 210)"$'\n' "$STDOUT"

flag session-record '{"type": "token_usage_record", "payload": {"usage": {"input_tokens": 230000}}}'
expect_equal "reads a Codex token_usage_record" "$(message_for 230)"$'\n' "$STDOUT"

flag session-last "$(claude_usage 300000 0 0)"$'\n'"$(claude_usage 100000 0 0)"
expect_equal "the last usage line wins" "" "$STDOUT"

flag session-absent "$(head -c 840000 /dev/zero | tr '\0' x)"
expect_equal "no usage means no nudge" "" "$STDOUT"
expect_equal "no usage exits 0" 0 "$STATUS"

flag session-default "$(claude_usage 210000 0 0)"
expect_equal "context mode is the default with no arguments" "$(message_for 210)"$'\n' "$STDOUT"

flag session-quiet "$(claude_usage 199999 0 0)"
expect_equal "quiet below the threshold" "" "$STDOUT"

flag session-2 "$(claude_usage 210000 0 0)"
expect_contains "plain text starts with the tag" "[handoff-token-flag]" "${STDOUT:0:20}"
expect_contains "plain text names the size" 210k "$STDOUT"
expect_contains "plain text names the handoff skill" handoff "$STDOUT"
expect_equal "plain text is not JSON" invalid "$(jq -e . <<<"$STDOUT" >/dev/null 2>&1 && echo json || echo invalid)"

flag session-3 "$(claude_usage 210000 0 0)"
first=$STDOUT
flag session-3 "$(claude_usage 240000 0 0)"
same_band=$STDOUT
flag session-3 "$(claude_usage 260000 0 0)"
next_band=$STDOUT
expect_equal "first crossing nudges" "$(message_for 210)"$'\n' "$first"
expect_equal "same band stays quiet" "" "$same_band"
expect_equal "next band nudges again" "$(message_for 260)"$'\n' "$next_band"
expect_equal "band state is recorded per session" 1 "$(cat "$TMPDIR/dotai-handoff-flag-session-3.txt")"

flag session-4 "$(claude_usage 210000 0 0)"
mine=$STDOUT
flag session-5 "$(claude_usage 210000 0 0)"
expect_equal "sessions track bands separately (mine)" "$(message_for 210)"$'\n' "$mine"
expect_equal "sessions track bands separately (theirs)" "$(message_for 210)"$'\n' "$STDOUT"

flag session-even "$(claude_usage 250500 0 0)"
expect_equal "a half rounds to the even neighbour (down)" "$(message_for 250)"$'\n' "$STDOUT"
flag session-odd "$(claude_usage 251500 0 0)"
expect_equal "a half rounds to the even neighbour (up)" "$(message_for 252)"$'\n' "$STDOUT"

flag 'we/ird:id' "$(claude_usage 210000 0 0)"
expect_equal "an unsafe session id is sanitized for the state file" 0 \
  "$([ -f "$TMPDIR/dotai-handoff-flag-weirdid.txt" ] && echo 0 || echo 1)"

run_hook "$HOOK" <<<'{"transcript_path": "/nonexistent/x.jsonl"}'
expect_equal "missing transcript exits 0" 0 "$STATUS"
expect_equal "missing transcript prints nothing" "" "$STDOUT"
run_hook "$HOOK" <<<'not json'
expect_equal "malformed input exits 0 silently" "0:" "$STATUS:$STDOUT"

# Each harness config runs the hook and gets the nudge.
transcript="$WORK/wired.jsonl"
claude_usage 210000 0 0 >"$transcript"
export PLUGIN_ROOT="$PLUGIN_ROOT_DIR" CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT_DIR"
for wiring in "claude hooks/claude-hooks.json" "codex hooks/codex-hooks.json"; do
  read -r harness config <<<"$wiring"
  count=0
  while IFS= read -r command; do
    count=$((count + 1))
    expect_contains "$config runs the hook in context mode" "handoff-token-flag." "$command"
    run_wiring "$harness" "$command" <<<"$(jq -cn --arg t "$transcript" --arg s "wired-$harness" '{transcript_path: $t, session_id: $s}')"
    expect_equal "$config command nudges" "$(message_for 210)"$'\n' "$STDOUT"
  done < <(wiring_commands "$harness" "$PLUGIN_ROOT_DIR/$config" UserPromptSubmit)
  expect_equal "$config wires one UserPromptSubmit hook" 1 "$count"
  [ "$harness" = codex ] || continue
  while IFS= read -r command; do
    run_windows_wiring "$command" "$HOOKS_DIR" <<<"$(jq -cn --arg t "$transcript" '{transcript_path: $t, session_id: "wired-windows"}')"
    expect_equal "$config Windows command nudges" "$(message_for 210)"$'\n' "$STDOUT"
  done < <(windows_commands codex "$PLUGIN_ROOT_DIR/$config" UserPromptSubmit)
done

finish
