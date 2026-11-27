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

copilot_config=$(jq -r '.hooks' "$PLUGIN_ROOT_DIR/plugin.json")
for wiring in "claude hooks/claude-hooks.json PreToolUse 2" "codex hooks/codex-hooks.json PreToolUse 1" "copilot $copilot_config preToolUse 2"; do
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

# Devin supplies a project root and may omit cwd from the hook payload.
config="$PLUGIN_ROOT_DIR/hooks.json"
unset PLUGIN_ROOT CLAUDE_PLUGIN_ROOT
export DEVIN_PLUGIN_ROOT="$PLUGIN_ROOT_DIR" DEVIN_PROJECT_DIR="$WORK"
for tool in read exec; do
  command=$(jq -r --arg m "^$tool\$" '.PreToolUse[] | select(.matcher == $m) | .hooks[].command' "$config")
  case "$tool" in
    read)
      full='{"tool_name":"read","tool_input":{"path":"big.txt"}}'
      targeted='{"tool_name":"read","tool_input":{"file_path":"big.txt","offset":24,"limit":12}}'
      ;;
    exec)
      full='{"tool_name":"exec","tool_input":{"command":"cat big.txt"}}'
      targeted='{"tool_name":"exec","tool_input":{"command":"sed -n '\''1,20p'\'' big.txt"}}'
      ;;
  esac
  run_wiring devin "$command" <<<"$full"
  expect_equal "Devin $tool exits 0" 0 "$STATUS"
  expect_equal "Devin $tool blocks a full 480-line read" block "$(jq -r '.decision' <<<"$STDOUT")"
  expect_contains "Devin $tool suggests bulk-reader" bulk-reader "$(jq -r '.reason' <<<"$STDOUT")"
  run_wiring devin "$command" <<<"$targeted"
  expect_equal "Devin $tool allows a targeted read" "" "$STDOUT"
done

mkdir "$WORK/other"
seq 1 500 >"$WORK/other/big.txt"
exec_command=$(jq -r '.PreToolUse[] | select(.matcher == "^exec$") | .hooks[].command' "$config")
workdir_input=$(jq -cn --arg cwd "$WORK" --arg workdir "$WORK/other" \
  '{tool_name: "exec", cwd: $cwd, tool_input: {command: "cat big.txt", workdir: $workdir}}')
run_wiring devin "$exec_command" <<<"$workdir_input"
expect_equal "Devin exec blocks a large read in tool_input.workdir" block "$(jq -r '.decision' <<<"$STDOUT")"
expect_contains "Devin exec reads tool_input.workdir before the 480-line fallback" "500-line file" "$(jq -r '.reason' <<<"$STDOUT")"

# The launcher's batch half runs bash with a backslash-only path, which Git
# Bash leaves as it is. On Linux a backslash is a plain filename character, so
# the hook is copied to a file named like that Windows path, beside a directory
# named like its directory part, and run from a cwd with no hook-json.awk.
win_dir='C:\plugin\hooks'
mkdir "$WORK/$win_dir"
cp "$PLUGIN_ROOT_DIR/hooks/hook-json.awk" "$WORK/$win_dir/"
for hook in check-file-size check-bash-read; do
  cp "$PLUGIN_ROOT_DIR/hooks/$hook" "$WORK/$win_dir\\$hook"
  case "$hook" in
    check-file-size) input=$read_input ;;
    *) input=$bash_input ;;
  esac
  capture bash -c 'cd "$1" && exec bash "$2" --harness copilot' _ "$WORK" "$win_dir\\$hook" <<<"$input"
  expect_equal "$hook run by a backslash path denies a 480-line read" deny \
    "$(jq -r '.permissionDecision' <<<"$STDOUT" 2>/dev/null)"
done

finish
