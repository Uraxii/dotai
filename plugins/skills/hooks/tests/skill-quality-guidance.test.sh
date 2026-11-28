#!/bin/bash
# Each harness config adds the skill-quality guidance once per session and
# skill directory, on Linux and macOS and through the Windows launcher.

PLUGIN_ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=../../../../scripts/hook-test-assertions.sh
. "$PLUGIN_ROOT_DIR/../../scripts/hook-test-assertions.sh"

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
export PLUGIN_ROOT="$PLUGIN_ROOT_DIR" CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT_DIR" TMPDIR="$WORK"
hook="$PLUGIN_ROOT_DIR/hooks/skill-quality-guidance"
skill_a="$WORK/repo/skills/alpha"
skill_b="$WORK/repo/skills/beta"
mkdir -p "$skill_a" "$skill_b" "$WORK/repo/plugin/hooks/tests" "$skill_a/examples/skills/inner"
# clean_skill DIR: a SKILL.md that passes the lint, so the lint adds nothing.
clean_skill() {
  mkdir -p "$1"
  printf -- '---\nname: %s\ndescription: Checks widgets. Use when a widget breaks.\n---\n\nBody.\n' "${1##*/}" >"$1/SKILL.md"
}
clean_skill "$skill_a"
clean_skill "$skill_b"

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
  run_windows_wiring "$command" "$PLUGIN_ROOT_DIR/hooks" <<<"$(input "$harness" "$session-win" "$skill_a/SKILL.md")"
  expect_contains "$harness: Windows command adds the guidance" "## Under-specified guidance" "$(context)"
done

run_hook "$hook" --harness claude <<<"$(input claude s-shape "$skill_a/SKILL.md")"
expect_equal "claude output is PreToolUse context" PreToolUse "$(jq -r .hookSpecificOutput.hookEventName <<<"$STDOUT")"

run_hook "$hook" --harness codex <<<"$(input codex s-multi "$skill_a/SKILL.md" "$skill_b/references/y.md")"
expect_contains "codex patch with two files names the first skill" "- $skill_a" "$(context)"
expect_contains "codex patch with two files names the second skill" "- $skill_b" "$(context)"

run_hook "$hook" --harness claude <<<"$(jq -cn --arg c "$WORK/repo" '{session_id: "s-rel", cwd: $c, tool_input: {file_path: "skills/alpha/SKILL.md"}}')"
expect_contains "a relative path resolves against cwd" "- $WORK/repo/skills/alpha" "$(context)"

run_hook "$hook" --harness claude <<<"$(input claude s-new "$WORK/repo/skills/gamma/SKILL.md")"
expect_contains "creating a SKILL.md adds the guidance" "- $WORK/repo/skills/gamma" "$(context)"

run_hook "$hook" --harness claude <<<"$(input claude s-nested "$skill_a/examples/skills/inner/x.md")"
expect_contains "a skills folder inside a skill resolves to the outer skill" "- $skill_a" "$(context)"
expect_equal "the inner folder is not named" "" "$(context | grep -F "inner")"

run_hook "$hook" --harness other <<<"$(input claude s-x "$skill_a/SKILL.md")"
expect_equal "an unknown harness adds nothing" "" "$STDOUT"

# The lint runs after each edit and reports its FAIL and WARN lines.
skill_d="$WORK/repo/skills/delta"
clean_skill "$skill_d"
printf 'See [x](references/nope.md) when a widget breaks.\n' >>"$skill_d/SKILL.md"
for wiring in "claude hooks/claude-hooks.json PostToolUse" "codex hooks/codex-hooks.json PostToolUse" "copilot hooks.json postToolUse"; do
  read -r harness config event <<<"$wiring"
  command=$(wiring_commands "$harness" "$PLUGIN_ROOT_DIR/$config" "$event")
  session="s-lint-$harness"

  run_wiring "$harness" "$command" <<<"$(input "$harness" "$session" "$skill_d/SKILL.md")"
  expect_equal "$harness: lint hook exits 0 on a FAIL" 0 "$STATUS"
  expect_contains "$harness: lint hook reports the FAIL line" "FAIL  SKILL.md: link to references/nope.md does not resolve" "$(context)"
  expect_contains "$harness: lint hook names the skill directory" "$skill_d" "$(context)"
  run_wiring "$harness" "$command" <<<"$(input "$harness" "$session" "$skill_d/SKILL.md")"
  expect_contains "$harness: lint runs again on the next edit" "references/nope.md does not resolve" "$(context)"
  expect_equal "$harness: the guidance is not added twice" "" "$(context | grep -F '## Under-specified guidance')"
  [ "$harness" = copilot ] ||
    expect_equal "$harness: lint output is PostToolUse context" PostToolUse "$(jq -r .hookSpecificOutput.hookEventName <<<"$STDOUT")"

  run_wiring "$harness" "$command" <<<"$(input "$harness" "$session" "$WORK/repo/README.md")"
  expect_equal "$harness: lint hook ignores a file outside a skill" "" "$STDOUT"

  [ "$harness" = claude ] && continue
  command=$(windows_commands "$harness" "$PLUGIN_ROOT_DIR/$config" "$event")
  run_windows_wiring "$command" "$PLUGIN_ROOT_DIR/hooks" <<<"$(input "$harness" "$session-win" "$skill_d/SKILL.md")"
  expect_contains "$harness: Windows lint command reports the FAIL line" "references/nope.md does not resolve" "$(context)"
done

# Lint text is bounded: 200 bytes a line, 40 lines in all, with a notice.
skill_f="$WORK/repo/skills/phi"
clean_skill "$skill_f"
mkdir -p "$skill_f/references"
printf 'Read [p](references/p.md) when a widget breaks.\n' >>"$skill_f/SKILL.md"
printf -- '---\nshape: %s\n---\n' "$(head -c 200000 /dev/zero | tr '\0' x)" >"$skill_f/references/p.md"
run_hook "$hook" --harness claude --lint <<<"$(input claude s-big "$skill_f/SKILL.md")"
expect_equal "a 200 KB shape value gives valid JSON" "0 valid" "$STATUS $(jq -e .hookSpecificOutput.additionalContext <<<"$STDOUT" >/dev/null && echo valid)"
expect_contains "the long lint line is reported" "WARN  references/p.md: shape 'xxx" "$(context)"
expect_equal "the longest lint line is cut to 200 bytes" 200 "$(context | grep -F "shape 'xxx" | LC_ALL=C awk '{ print length($0) }')"
printf -- '---\nshape: none\n---\n' >"$skill_f/references/p.md"
for i in $(seq 30); do printf '[x](gone%s.md)\n' "$i"; done >>"$skill_f/references/p.md"
run_hook "$hook" --harness claude --lint <<<"$(input claude s-many "$skill_f/SKILL.md")"
expect_equal "40 lint lines are kept" 20 "$(context | grep -c '^FAIL  references/p.md: link to gone')"
expect_contains "the dropped lines get a notice" "[22 more lint lines are not shown." "$(context)"

patch=$(printf '*** Begin Patch\n'; for i in $(seq 150); do printf '*** Add File: %s/skills/%s-%0250d/SKILL.md\n+x\n' "$WORK/repo" "$i" 0; done; printf '*** End Patch')
run_hook "$hook" --harness codex <<<"$(jq -cn --arg c "$patch" '{session_id: "s-cap", tool_input: {command: $c}}')"
expect_contains "a context over 32,000 bytes is cut with a notice" "[The rest of this context was cut at 32000 bytes.]" "$(context)"
expect_equal "the cut context stays small" 1 "$(context | LC_ALL=C wc -c | awk '{ print ($1 <= 32100) }')"

# The lint runs only on a skill directory whose SKILL.md exists.
mkdir -p "$WORK/repo/skills/zeta"
run_hook "$hook" --harness claude --lint <<<"$(input claude s-guard "$WORK/repo/skills/zeta/SKILL.md")"
expect_equal "an edit that has not made the SKILL.md yet adds no lint line" "" "$(context | grep -F 'lint found these problems')"
expect_contains "it still adds the guidance" "- $WORK/repo/skills/zeta" "$(context)"

# A path that can leave the skill, or that holds a newline, is not a skill file.
run_hook "$hook" --harness claude <<<"$(input claude s-dots "$skill_a/../../docs/out.md")"
expect_equal "a path with a .. segment adds nothing" "" "$STDOUT"
run_hook "$hook" --harness claude --lint <<<"$(input claude s-dots-lint "$skill_d/../../docs/out.md")"
expect_equal "a path with a .. segment is not linted" "" "$STDOUT"
run_hook "$hook" --harness claude <<<"$(input claude s-newline "$skill_a/SKILL.md"$'\n'"/x.md")"
expect_equal "a path with a newline adds nothing" "" "$STDOUT"
run_hook "$hook" --harness copilot --lint <<<"$(input copilot s-newline "$skill_d/SKILL.md"$'\n'"/x.md")"
expect_equal "a copilot path with a newline is not linted" "" "$STDOUT"

# With no session id, PreToolUse adds the guidance and PostToolUse does not.
nosession=$(jq -cn --arg f "$skill_a/SKILL.md" '{tool_input: {file_path: $f}}')
run_hook "$hook" --harness claude <<<"$nosession"
expect_contains "no session: PreToolUse adds the guidance" "## Under-specified guidance" "$(context)"
run_hook "$hook" --harness claude --lint <<<"$nosession"
expect_equal "no session: PostToolUse on a clean skill adds nothing" "0 " "$STATUS $STDOUT"
run_hook "$hook" --harness copilot --lint <<<"$(jq -cn --arg f "$skill_a/SKILL.md" '{toolArgs: ({path: $f} | tojson)}')"
expect_contains "no session: Copilot, with no PreToolUse, adds the guidance" "## Under-specified guidance" "$(context)"

(cd "$WORK/repo" && run_hook "$hook" --harness claude <<<'{"session_id": "s-nocwd", "tool_input": {"file_path": "skills/alpha/SKILL.md"}}' && context) >"$WORK/nocwd"
expect_contains "a relative path with no cwd resolves against the current directory" "- ./skills/alpha" "$(cat "$WORK/nocwd")"

claude_pre=$(wiring_commands claude "$PLUGIN_ROOT_DIR/hooks/claude-hooks.json" PreToolUse)
claude_post=$(wiring_commands claude "$PLUGIN_ROOT_DIR/hooks/claude-hooks.json" PostToolUse)
run_wiring claude "$claude_pre" <<<"$(input claude s-clean "$skill_a/SKILL.md")"
run_wiring claude "$claude_post" <<<"$(input claude s-clean "$skill_a/SKILL.md")"
expect_equal "a clean skill after the guidance adds nothing" "0 " "$STATUS $STDOUT"

# A file with numbered steps or routes gets one pointer to the playbook reference.
skill_e="$WORK/repo/skills/epsilon"
clean_skill "$skill_e"
mkdir -p "$skill_e/references"
printf '1. Read.\n2. Fix.\n3. Verify.\n' >"$skill_e/references/steps.md"
run_hook "$hook" --harness claude <<<"$(input claude s-pointer "$skill_e/references/steps.md")"
expect_contains "a file with numbered steps adds the pointer" "holds numbered steps or routes" "$(context)"
run_hook "$hook" --harness claude <<<"$(input claude s-pointer "$skill_e/references/steps.md")"
expect_equal "the pointer is added once per session" "" "$STDOUT"

run_hook "$hook" --harness claude <<<"$(input claude s-late "$skill_e/SKILL.md")"
expect_equal "a file with no steps adds no pointer" "" "$(context | grep -F 'holds numbered steps or routes')"
run_hook "$hook" --harness claude <<<"$(input claude s-late "$skill_e/references/steps.md")"
expect_contains "a later edit with steps adds the pointer" "holds numbered steps or routes" "$(context)"
expect_equal "the later pointer comes without the guidance" "" "$(context | grep -F '## Under-specified guidance')"

run_hook "$hook" --harness claude <<<"$(jq -cn --arg f "$skill_e/references/new.md" '{session_id: "s-write", tool_input: {file_path: $f, content: "---\nshape: router\n---\n"}}')"
expect_contains "a Write whose content has a shape line adds the pointer" "holds numbered steps or routes" "$(context)"
run_hook "$hook" --harness codex <<<"$(jq -cn --arg c "$(printf '*** Begin Patch\n*** Add File: %s\n+1. Read.\n+2. Fix.\n+3. Verify.\n*** End Patch' "$skill_e/references/add.md")" '{session_id: "s-patch", tool_input: {command: $c}}')"
expect_contains "a codex patch that adds steps adds the pointer" "holds numbered steps or routes" "$(context)"

finish
