#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR=$(mktemp -d)
trap 'rm -rf "$WORKDIR"' EXIT
mkdir "$WORKDIR/bin"
for tool in cat jq wc tr grep sed; do
  ln -s "$(command -v "$tool")" "$WORKDIR/bin/$tool"
done
BASH_BIN=$(command -v bash)
seq 1 480 > "$WORKDIR/full.txt"
PASSED=0
FAILED=0

check() {
  local name="$1" expected="$2" actual="$3"
  if [ "$expected" = "$actual" ]; then
    printf '  PASS  %s\n' "$name"
    PASSED=$((PASSED + 1))
  else
    printf '  FAIL  %s expected=[%s] got=[%s]\n' "$name" "$expected" "$actual"
    FAILED=$((FAILED + 1))
  fi
}

invoke() {
  PATH="$WORKDIR/bin" SHUNT_MIN_LINES="$chunk" \
    "$BASH_BIN" "$SCRIPT_DIR/../hooks/$hook" --harness "$harness" <<< "$1"
}

# Copilot 1.0.95 has no subagent identity in observed preToolUse input. Its shared
# reason must let a reader continue without another task invocation.
while read -r harness hook agent_id chunk; do
  args=$(jq -cn --arg file "$WORKDIR/full.txt" \
    '{file_path: $file, path: $file, command: ("cat " + $file)}')
  input=$(jq -cn --argjson args "$args" --arg id "$agent_id" \
    '{tool_input: $args, toolArgs: $args} +
     (if $id == "parent" then {} else {agent_id: $id} end)')
  result=$(invoke "$input")
  reason=$(jq -r '.permissionDecisionReason // .hookSpecificOutput.permissionDecisionReason' <<< "$result")
  label="$harness/$hook/$agent_id"
  check "$label/deny" deny "$(jq -r '.permissionDecision // .hookSpecificOutput.permissionDecision' <<< "$result")"
  check "$label/chunks" true "$(jq -n --arg r "$reason" --arg chunk "$chunk" \
    '$r | contains("chunks of at most " + $chunk + " lines") and
     contains("full file") and contains("sed -n '\''START,ENDp'\'' FILE") and
     contains("grep") and contains("do not delegate again")')"
  if [ "$agent_id" = parent ]; then
    check "$label/delegate-first-without-portal" true "$(jq -n --arg r "$reason" \
      '$r | startswith("Delegate via the bulk-reader skill") and contains("exact content")')"
  else
    check "$label/subagent-no-recursion" false "$(jq -n --arg r "$reason" \
      '$r | contains("Delegate via")')"
  fi
  if [ "$hook" = check-file-size ] && [ "$harness" != codex ]; then
    if [ "$harness" = copilot ]; then
      check "$label/view-guidance" true "$(jq -n --arg r "$reason" \
        '$r | contains("view_range [start, end]")')"
      args=$(jq -c --argjson chunk "$chunk" '. + {view_range: [1, $chunk]}' <<< "$args")
    else
      check "$label/read-guidance" true "$(jq -n --arg r "$reason" --arg chunk "$chunk" \
        '$r | contains("offset=1, limit=" + $chunk)')"
      args=$(jq -c --argjson chunk "$chunk" '. + {offset: 1, limit: $chunk}' <<< "$args")
    fi
    input=$(jq -cn --argjson args "$args" --arg id "$agent_id" \
      '{tool_input: $args, toolArgs: $args, agent_id: $id}')
    check "$label/native-chunk-allowed" "" "$(invoke "$input")"
  fi
  hook=check-bash-read
  input=$(jq -cn --arg cmd "sed -n '1,${chunk}p' $WORKDIR/full.txt" \
    --arg id "$agent_id" \
    '{tool_input: {command: $cmd}, toolArgs: {command: $cmd}, agent_id: $id}')
  check "$label/bash-chunk-allowed" "" "$(invoke "$input")"
done <<'CASES'
claude check-file-size parent 350
claude check-file-size reader 350
claude check-bash-read reader 200
copilot check-file-size parent 350
copilot check-bash-read parent 350
codex check-bash-read parent 350
CASES

sed -n '1,350p' "$WORKDIR/full.txt" > "$WORKDIR/chunks.txt"
sed -n '351,480p' "$WORKDIR/full.txt" >> "$WORKDIR/chunks.txt"
check "sed-chunks-read-full-file" "$(cat "$WORKDIR/full.txt")" "$(cat "$WORKDIR/chunks.txt")"
printf '## %d %d\n' "$PASSED" "$FAILED"
[ "$FAILED" -eq 0 ]
