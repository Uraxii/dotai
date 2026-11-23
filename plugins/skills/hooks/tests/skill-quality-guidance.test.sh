#!/bin/bash
# Each harness config adds the skill-quality guidance once per session and
# skill directory, on Linux and macOS and with the Windows command's
# arguments.

PLUGIN_ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=../../../../scripts/hook-test-assertions.sh
. "$PLUGIN_ROOT_DIR/../../scripts/hook-test-assertions.sh"

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
export PLUGIN_ROOT="$PLUGIN_ROOT_DIR" CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT_DIR" TMPDIR="$WORK"
hook="$PLUGIN_ROOT_DIR/hooks/skill_quality_guidance.py"
skill_a="$WORK/repo/skills/alpha"
skill_b="$WORK/repo/skills/beta"
mkdir -p "$skill_a" "$skill_b" "$WORK/repo/plugin/hooks/tests" "$skill_a/examples/skills/inner"
touch "$skill_a/SKILL.md" "$skill_b/SKILL.md"

# input HARNESS SESSION PATH...: an edit of each PATH in that harness's shape.
input() {
  local harness=$1 session=$2 patch
  shift 2
  case "$harness" in
    claude) jq -cn --arg s "$session" --arg f "$1" '{session_id: $s, tool_input: {file_path: $f}}' ;;
    codex)
      patch=$(printf '*** Begin Patch\n'; printf '*** Update File: %s\n@@\n-a\n+b\n' "$@"; printf '*** End Patch')
      jq -cn --arg s "$session" --arg c "$patch" '{session_id: $s, tool_input: {command: $c}}'
      ;;
    copilot) jq -cn --arg s "$session" --arg f "$1" '{sessionId: $s, toolArgs: ({path: $f} | tojson)}' ;;
  esac
}

# run_windows_python COMMAND: runs the hook with the arguments the Windows
# command passes to py -3. PowerShell is not available here, so the test
# replays those arguments rather than the command itself.
run_windows_python() {
  local args
  args=$(sed -nE 's/.*py -3 (.*) 2>\$null; if .*/\1/p' <<<"$1" | tr -d "'\"")
  args=${args//\$env:PLUGIN_ROOT/$PLUGIN_ROOT}
  args=${args//\$\{PLUGIN_ROOT\}/$PLUGIN_ROOT}
  # The arguments are plain words, so word splitting rebuilds them.
  # shellcheck disable=SC2086
  run_python_hook ${args//\\//}
}

context() {
  jq -r '.additionalContext // .hookSpecificOutput.additionalContext // empty' <<<"$STDOUT" 2>/dev/null
}

for wiring in "claude hooks/claude-hooks.json PreToolUse" "codex hooks/codex-hooks.json PreToolUse" "copilot hooks.json postToolUse"; do
  read -r harness config event <<<"$wiring"
  command=$(wiring_commands "$harness" "$PLUGIN_ROOT_DIR/$config" "$event")
  session="s-$harness"

  run_wiring "$harness" "$command" <<<"$(input "$harness" "$session" "$skill_a/SKILL.md")"
  expect_equal "$harness: exits 0" 0 "$STATUS"
  expect_contains "$harness: SKILL.md edit adds the guidance" "## Under-specified guidance" "$(context)"
  expect_contains "$harness: guidance names the skill directory" "- $skill_a" "$(context)"
  expect_contains "$harness: guidance names the verification script" "skills/skill-quality/scripts/lint-skills.sh" "$(context)"

  run_wiring "$harness" "$command" <<<"$(input "$harness" "$session" "$skill_a/references/x.md")"
  expect_equal "$harness: second edit in the same skill adds nothing" "" "$STDOUT"

  run_wiring "$harness" "$command" <<<"$(input "$harness" "$session" "$skill_b/references/x.md")"
  expect_contains "$harness: reference edit in a second skill adds the guidance" "- $skill_b" "$(context)"

  for path in "$WORK/repo/README.md" "$WORK/repo/skills/gamma/run.sh" "$WORK/repo/skills/notes.md" \
    "$WORK/repo/skills/gamma/references/x.md" "$WORK/repo/plugin/hooks/tests/README.md"; do
    run_wiring "$harness" "$command" <<<"$(input "$harness" "$session-other" "$path")"
    expect_equal "$harness: $path adds nothing" "" "$STDOUT"
  done

  [ "$harness" = claude ] && continue
  command=$(windows_commands "$harness" "$PLUGIN_ROOT_DIR/$config" "$event")
  run_windows_python "$command" <<<"$(input "$harness" "$session-win" "$skill_a/SKILL.md")"
  expect_contains "$harness: Windows command adds the guidance" "## Under-specified guidance" "$(context)"
  expect_contains "$harness: Windows command falls back to python" "{ python " "$command"
  expect_contains "$harness: Windows command exits 0 without Python" 'if (-not $?) { $LASTEXITCODE = 0 }; exit $LASTEXITCODE' "$command"
done

run_python_hook "$hook" --harness claude <<<"$(input claude s-shape "$skill_a/SKILL.md")"
expect_equal "claude output is PreToolUse context" PreToolUse "$(jq -r .hookSpecificOutput.hookEventName <<<"$STDOUT")"

run_python_hook "$hook" --harness codex <<<"$(input codex s-multi "$skill_a/SKILL.md" "$skill_b/references/y.md")"
expect_contains "codex patch with two files names the first skill" "- $skill_a" "$(context)"
expect_contains "codex patch with two files names the second skill" "- $skill_b" "$(context)"

run_python_hook "$hook" --harness claude <<<"$(jq -cn --arg c "$WORK/repo" '{session_id: "s-rel", cwd: $c, tool_input: {file_path: "skills/alpha/SKILL.md"}}')"
expect_contains "a relative path resolves against cwd" "- $WORK/repo/skills/alpha" "$(context)"

run_python_hook "$hook" --harness claude <<<"$(input claude s-new "$WORK/repo/skills/gamma/SKILL.md")"
expect_contains "creating a SKILL.md adds the guidance" "- $WORK/repo/skills/gamma" "$(context)"

run_python_hook "$hook" --harness claude <<<"$(input claude s-nested "$skill_a/examples/skills/inner/x.md")"
expect_contains "a skills folder inside a skill resolves to the outer skill" "- $skill_a" "$(context)"
expect_equal "the inner folder is not named" "" "$(context | grep -F "inner")"

run_python_hook "$hook" --harness other <<<"$(input claude s-x "$skill_a/SKILL.md")"
expect_equal "an unknown harness adds nothing" "" "$STDOUT"

for stdin in '' 'not json' '[1]' '{"session_id": "s-bad", "tool_input": 5}' '{"sessionId": "s-bad", "toolArgs": "{bad"}'; do
  for harness in claude codex copilot; do
    run_python_hook "$hook" --harness "$harness" <<<"$stdin"
    expect_equal "$harness: input '$stdin' exits 0" 0 "$STATUS"
    expect_equal "$harness: input '$stdin' adds nothing" "" "$STDOUT"
  done
done

finish
