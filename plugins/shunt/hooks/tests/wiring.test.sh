#!/bin/bash
# Each harness config runs both shunt hooks, on Linux and macOS and through
# the Windows launcher's bash half. evals/run.sh covers the decisions.

PLUGIN_ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=../../../../scripts/hook-test-assertions.sh
. "$PLUGIN_ROOT_DIR/../../scripts/hook-test-assertions.sh"

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
seq 1 480 >"$WORK/big.txt"
export PLUGIN_ROOT="$PLUGIN_ROOT_DIR" CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT_DIR"

read_input=$(jq -cn --arg f "$WORK/big.txt" '{tool_input: {file_path: $f}, toolArgs: {path: $f}}')
bash_input=$(jq -cn --arg c "cat $WORK/big.txt" '{tool_input: {command: $c}, toolArgs: {command: $c}}')

for wiring in "claude hooks/claude-hooks.json PreToolUse 2" "codex hooks/codex-hooks.json PreToolUse 1" "copilot hooks.json preToolUse 2"; do
  read -r harness config event expected_count <<<"$wiring"
  count=0
  while IFS= read -r command; do
    count=$((count + 1))
    case "$command" in
      *check-file-size*) input=$read_input ;;
      *) input=$bash_input ;;
    esac
    run_wiring "$harness" "$command" <<<"$input"
    expect_equal "$config command exits 0: $command" 0 "$STATUS"
    expect_equal "$config command denies a 480-line read: $command" deny \
      "$(jq -r '.permissionDecision // .hookSpecificOutput.permissionDecision' <<<"$STDOUT" 2>/dev/null)"
  done < <(wiring_commands "$harness" "$PLUGIN_ROOT_DIR/$config" "$event")
  expect_equal "$config wires $expected_count hooks" "$expected_count" "$count"
  [ "$harness" = claude ] && continue
  while IFS= read -r command; do
    case "$command" in
      *check-file-size*) input=$read_input ;;
      *) input=$bash_input ;;
    esac
    run_windows_wiring "$command" "$PLUGIN_ROOT_DIR/hooks" <<<"$input"
    expect_equal "$config Windows command denies a 480-line read: $command" deny \
      "$(jq -r '.permissionDecision // .hookSpecificOutput.permissionDecision' <<<"$STDOUT" 2>/dev/null)"
  done < <(windows_commands "$harness" "$PLUGIN_ROOT_DIR/$config" "$event")
done

finish
