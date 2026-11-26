#!/bin/bash
# Behavior tests for inject_instructions.sh.

HOOKS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REAL_PLUGIN_ROOT="$(dirname "$HOOKS_DIR")"
# shellcheck source=../../../../scripts/hook-test-assertions.sh
. "$REAL_PLUGIN_ROOT/../../scripts/hook-test-assertions.sh"

FIXTURE_TEXT=$'# Fixture rules\n\n- Say "hi" first.\n- Line with a \\ backslash.'
MAIN_FIXTURE_TEXT='# Main agent fixture rules'
MAIN_FILE=main-agent-instructions.md
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

# make_plugin_root DIR [INSTRUCTIONS [MAIN_INSTRUCTIONS]]: an unset argument
# leaves that file out.
make_plugin_root() {
  mkdir -p "$1/hooks"
  cp "$HOOKS_DIR"/inject_instructions.* "$HOOKS_DIR/hook-json.awk" "$HOOKS_DIR/run-hook.cmd" "$1/hooks/"
  [ $# -ge 2 ] && printf '%s' "$2" >"$1/instructions.md"
  [ $# -ge 3 ] && printf '%s' "$3" >"$1/$MAIN_FILE"
}

ROOT="$WORK/root"
make_plugin_root "$ROOT" "$FIXTURE_TEXT" "$MAIN_FIXTURE_TEXT"
HOOK="$ROOT/hooks/inject_instructions.sh"

run_hook "$HOOK" --harness claude --event SessionStart </dev/null
expect_equal "claude session output is the file text" "$FIXTURE_TEXT"$'\n' "$STDOUT"
expect_equal "claude session exits 0" 0 "$STATUS"

for case in "claude SubagentStart" "codex SessionStart" "codex SubagentStart"; do
  read -r harness event <<<"$case"
  run_hook "$HOOK" --harness "$harness" --event "$event" </dev/null
  expect_json "hook-specific JSON echoes the event ($case)" \
    "$(jq -cn --arg e "$event" --arg t "$FIXTURE_TEXT" '{hookSpecificOutput: {hookEventName: $e, additionalContext: $t}}')" "$STDOUT"
done

for event in SessionStart SubagentStart; do
  run_hook "$HOOK" --harness copilot --event "$event" </dev/null
  expect_json "copilot output is additionalContext JSON ($event)" \
    "$(jq -cn --arg t "$FIXTURE_TEXT" '{additionalContext: $t}')" "$STDOUT"
done

run_hook "$HOOK" --harness claude --file "$MAIN_FILE" </dev/null
expect_equal "--file selects the main agent file" "$MAIN_FIXTURE_TEXT"$'\n' "$STDOUT"

printf 'leaked' >"$ROOT/other.md"
for name in other.md ../instructions.md hooks/inject_instructions.sh; do
  run_hook "$HOOK" --harness claude --file "$name" </dev/null
  expect_equal "unknown file name $name exits 0" 0 "$STATUS"
  expect_equal "unknown file name $name prints nothing" "" "$STDOUT"
  expect_contains "unknown file name $name is rejected" "invalid choice" "$STDERR"
done

make_plugin_root "$WORK/no-main" "$FIXTURE_TEXT"
run_hook "$WORK/no-main/hooks/inject_instructions.sh" --harness codex --file "$MAIN_FILE" </dev/null
expect_equal "missing main file exits 0" 0 "$STATUS"
expect_equal "missing main file prints nothing" "" "$STDOUT"
expect_equal "missing main file is silent" "" "$STDERR"

mkdir "$WORK/elsewhere"
cd "$WORK/elsewhere" || exit 1
run_hook "$HOOK" --harness claude </dev/null
cd - >/dev/null || exit 1
expect_equal "finds the file from a different cwd" "$FIXTURE_TEXT"$'\n' "$STDOUT"

for label in missing empty blank; do
  case "$label" in
    missing) make_plugin_root "$WORK/$label" ;;
    empty) make_plugin_root "$WORK/$label" "" ;;
    blank) make_plugin_root "$WORK/$label" $' \n\n' ;;
  esac
  for harness in claude codex copilot; do
    run_hook "$WORK/$label/hooks/inject_instructions.sh" --harness "$harness" --event SubagentStart </dev/null
    expect_equal "$label file, $harness: exits 0" 0 "$STATUS"
    expect_equal "$label file, $harness: prints nothing" "" "$STDOUT"
    expect_equal "$label file, $harness: is silent" "" "$STDERR"
  done
done

make_plugin_root "$WORK/bad-utf8"
printf '\xff\xfe not utf-8' >"$WORK/bad-utf8/instructions.md"
run_hook "$WORK/bad-utf8/hooks/inject_instructions.sh" --harness claude </dev/null
expect_equal "unreadable file exits 0" 0 "$STATUS"
expect_equal "unreadable file prints nothing" "" "$STDOUT"
expect_equal "unreadable file writes one stderr line" 1 "$(printf '%s' "$STDERR" | grep -c '')"
expect_contains "unreadable file names the decode error" UnicodeDecodeError "$STDERR"

# Each harness config runs both files on session start and only the shared
# file on subagent start, from a plugin root with spaces in its path.
SPACED_ROOT="$WORK/plugin root with spaces"
make_plugin_root "$SPACED_ROOT" "$FIXTURE_TEXT" "$MAIN_FIXTURE_TEXT"
export PLUGIN_ROOT="$SPACED_ROOT" CLAUDE_PLUGIN_ROOT="$SPACED_ROOT"
cd "$WORK/elsewhere" || exit 1
copilot_config=$(jq -r '.hooks' "$REAL_PLUGIN_ROOT/plugin.json")
for wiring in "claude hooks/claude-hooks.json SessionStart SubagentStart" \
  "codex hooks/codex-hooks.json SessionStart SubagentStart" \
  "copilot $copilot_config sessionStart subagentStart"; do
  read -r harness config session_event subagent_event <<<"$wiring"
  expect_equal "$config wires exactly the two events" \
    "$(printf '%s\n' "$session_event" "$subagent_event" | sort | jq -Rsc 'split("\n") | map(select(. != ""))')" \
    "$(jq -c '.hooks | keys' "$REAL_PLUGIN_ROOT/$config")"
  for event in "$session_event" "$subagent_event"; do
    injections=
    while IFS= read -r command; do
      run_wiring "$harness" "$command" </dev/null
      expect_equal "$config $event command exits 0: $command" 0 "$STATUS"
      found=
      for marker in "# Fixture rules" "# Main agent"; do
        [[ "$STDOUT" == *"$marker"* ]] && found="$found[$marker]"
      done
      injections="$injections{$found}"
    done < <(wiring_commands "$harness" "$REAL_PLUGIN_ROOT/$config" "$event")
    windows_injections=
    while IFS= read -r command; do
      [ "$harness" = claude ] && break
      run_windows_wiring "$command" "$SPACED_ROOT/hooks" </dev/null
      expect_equal "$config $event Windows command exits 0: $command" 0 "$STATUS"
      found=
      for marker in "# Fixture rules" "# Main agent"; do
        [[ "$STDOUT" == *"$marker"* ]] && found="$found[$marker]"
      done
      windows_injections="$windows_injections{$found}"
    done < <(windows_commands "$harness" "$REAL_PLUGIN_ROOT/$config" "$event")
    if [ "$event" = "$session_event" ]; then
      expected="{[# Fixture rules]}{[# Main agent]}"
    else
      expected="{[# Fixture rules]}"
    fi
    expect_equal "$config $event injections" "$expected" "$injections"
    [ "$harness" = claude ] || expect_equal "$config $event Windows injections" "$expected" "$windows_injections"
  done
done

expect_equal "claude SessionStart entries share one matcher" 1 \
  "$(jq '[.hooks.SessionStart[].matcher] | unique | length' "$REAL_PLUGIN_ROOT/hooks/claude-hooks.json")"

expect_equal "Devin rule contains both instruction sources" \
  "$(printf '%s\n\n%s' "$(sed 's/[[:blank:]]*$//' "$REAL_PLUGIN_ROOT/instructions.md")" \
    "$(sed 's/[[:blank:]]*$//' "$REAL_PLUGIN_ROOT/$MAIN_FILE")")" \
  "$(sed '1,2d' "$REAL_PLUGIN_ROOT/AGENTS.md")"
expect_equal "Devin does not discover a root injection hook" no \
  "$([ -e "$REAL_PLUGIN_ROOT/hooks.json" ] && echo yes || echo no)"

capture python3 -B - "$REAL_PLUGIN_ROOT/../.." "$WORK" <<'PY'
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import runpy
import sys

repo, work = map(Path, sys.argv[1:])
generator = runpy.run_path(str(repo / "scripts/generate-plugin-manifests.py"))
for name in (None, "instructions.md", "main-agent-instructions.md"):
    root = work / ("generate-" + (name or "no-sources"))
    plugin = root / "plugins/personal-instructions"
    plugin.mkdir(parents=True)
    (root / "README.md").write_text((repo / "README.md").read_text())
    if name:
        (plugin / name).write_text("# Only available rules\n")
    with redirect_stdout(StringIO()):
        assert generator["main"]([], root=root) == 0
    rule = plugin / "AGENTS.md"
    if name:
        assert rule.read_text().splitlines()[2:] == ["# Only available rules"]
    else:
        assert not rule.exists()
PY
expect_equal "Devin generator handles missing instruction sources" 0 "$STATUS"
expect_equal "Devin generator reports no errors for missing sources" "" "$STDERR"

capture python3 -B - "$REAL_PLUGIN_ROOT/../.." "$WORK" <<'PY'
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import runpy
from shutil import copytree, ignore_patterns
import sys

repo, work = map(Path, sys.argv[1:])
generator = runpy.run_path(str(repo / "scripts/generate-plugin-manifests.py"))
root = work / "stale-rule"
copytree(repo, root, ignore=ignore_patterns(".git", ".fixtures"))
plugin = root / "plugins/personal-instructions"
rule = plugin / "AGENTS.md"
(plugin / "instructions.md").unlink()
(plugin / "main-agent-instructions.md").unlink()
original = rule.read_bytes()
output = StringIO()
with redirect_stdout(output):
    assert generator["main"](["--check"], root=root) == 2
    assert "generated Devin rules have no instruction sources" in output.getvalue()
    assert "plugins/personal-instructions/AGENTS.md" in output.getvalue()
    assert rule.read_bytes() == original
    assert generator["main"]([], root=root) == 0
    assert not rule.exists()
    assert generator["main"](["--check"], root=root) == 0
    rule.write_text("# Handwritten rules\n")
    assert generator["main"](["--check"], root=root) == 0
    assert generator["main"]([], root=root) == 0
    assert rule.read_text() == "# Handwritten rules\n"
PY
expect_equal "Devin generator flags and removes stale generated rules but preserves handwritten rules" 0 "$STATUS"
expect_equal "stale rule checks report no unexpected errors" "" "$STDERR"

finish
