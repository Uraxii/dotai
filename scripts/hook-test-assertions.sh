# Sourced by each plugins/*/hooks/tests/*.test.sh file. Every test runs the
# real hook as a subprocess, the way a harness does, with a jq on PATH that
# fails: Git for Windows ships no jq, so the hooks must not need it.

PASSED=0
FAILED=0
NO_JQ_DIR=$(mktemp -d)
printf '#!/bin/sh\necho "jq is not installed on Windows" >&2\nexit 127\n' >"$NO_JQ_DIR/jq"
chmod +x "$NO_JQ_DIR/jq"

# Runs a command with stdin passed through. Sets STDOUT and STDERR, both with
# trailing newlines kept, and STATUS.
capture() {
  local out_file err_file
  out_file=$(mktemp)
  err_file=$(mktemp)
  env PATH="$NO_JQ_DIR:$PATH" "$@" >"$out_file" 2>"$err_file"
  STATUS=$?
  IFS= read -rd '' STDOUT <"$out_file"
  IFS= read -rd '' STDERR <"$err_file"
  rm -f "$out_file" "$err_file"
}

# run_hook HOOK_SCRIPT [ARG...]: stdin is the hook input.
run_hook() {
  capture bash "$@"
}

# Prints, one per line, the commands a harness config runs for EVENT on Linux
# and macOS: Claude's and Codex's command key, and Copilot's bash key.
wiring_commands() {
  local harness="$1" config="$2" event="$3" key=command
  [ "$harness" = copilot ] && key=bash
  jq -r --arg event "$event" --arg key "$key" '.hooks[$event][] | (.hooks // [.])[] | .[$key]' "$config"
}

# Prints the Windows commands: Codex's commandWindows, Copilot's powershell key.
windows_commands() {
  local harness="$1" config="$2" event="$3" key=commandWindows
  [ "$harness" = copilot ] && key=powershell
  jq -r --arg event "$event" --arg key "$key" '.hooks[$event][] | (.hooks // [.])[] | .[$key]' "$config"
}

# run_wiring HARNESS COMMAND: runs a command from wiring_commands.
run_wiring() {
  capture bash -c "$2"
}

# Runs a Windows config command through the launcher's bash half, which is
# what cmd.exe hands the same script and arguments to. The test cannot run the
# batch half; it checks that the command names the launcher.
run_windows_wiring() {
  local command="$1" hooks_dir="$2" rest
  case "$command" in
    *'"${PLUGIN_ROOT}/hooks/run-hook.cmd" '* | *'"${PLUGIN_ROOT}\hooks\run-hook.cmd" '*) rest=${command#*run-hook.cmd\" } ;;
    *)
      STATUS="no launcher in: $command"
      STDOUT=
      return
      ;;
  esac
  # The arguments are plain words, so word splitting rebuilds them.
  # shellcheck disable=SC2086
  capture bash "$hooks_dir/run-hook.cmd" $rest
}

expect_equal() {
  local name="$1" expected="$2" actual="$3"
  if [ "$expected" == "$actual" ]; then
    PASSED=$((PASSED + 1))
  else
    FAILED=$((FAILED + 1))
    printf '  FAIL  %s\n    expected: %s\n    actual:   %s\n' "$name" "$expected" "$actual"
  fi
}

expect_contains() {
  local name="$1" needle="$2" haystack="$3"
  if [[ "$haystack" == *"$needle"* ]]; then
    PASSED=$((PASSED + 1))
  else
    FAILED=$((FAILED + 1))
    printf '  FAIL  %s\n    expected to contain: %s\n    actual: %s\n' "$name" "$needle" "$haystack"
  fi
}

# Canonical JSON, so key order and escaping style do not count as a difference.
canonical_json() {
  jq -cS . <<<"$1" 2>/dev/null || printf 'not json: %s' "$1"
}

expect_json() {
  expect_equal "$1" "$(canonical_json "$2")" "$(canonical_json "$3")"
}

# Prints the summary line run-hook-tests.sh reads, and sets the exit status.
finish() {
  rm -rf "$NO_JQ_DIR"
  printf '%s: %d passed, %d failed\n' "$(basename "$0")" "$PASSED" "$FAILED"
  [ "$FAILED" -eq 0 ]
}
