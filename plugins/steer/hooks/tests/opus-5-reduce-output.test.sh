#!/bin/bash
# Behavior tests for opus_5_reduce_output. 

HOOKS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLUGIN_ROOT_DIR="$(dirname "$HOOKS_DIR")"
# shellcheck source=../../../../scripts/hook-test-assertions.sh
. "$PLUGIN_ROOT_DIR/../../scripts/hook-test-assertions.sh"

HOOK="$HOOKS_DIR/opus_5_reduce_output.sh"
RECAP_INSTRUCTION='Write a plain recap in a few sentences about what changed and why it matters. Do not write a report, headers, or structured output. The reader has not seen the code, so use no paths, identifiers, line numbers, or code blocks. Leave out caveats and next steps unless something is broken or unfinished.'
BLOCK=$(jq -cn --arg r "$RECAP_INSTRUCTION" '{decision: "block", reason: $r}')
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
# Never touch the real ~/.claude/clean-recap.log, and never let an ambient
# override decide a gate under test.
export CLEAN_RECAP_LOG="$WORK/clean-recap.log"
unset CLEAN_RECAP_MODEL_PATTERN CLEAN_RECAP_LOG_MAX_BYTES

user_prompt() { jq -cn --arg t "${1:-do the thing}" '{type: "user", message: {content: $t}}'; }
tool_result() { echo '{"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "toolu_first", "content": "ok"}]}}'; }
injected_prompt() { echo '{"type": "user", "isMeta": true, "message": {"content": [{"type": "text", "text": "Base directory for this skill: /workspace/skills/x"}]}}'; }
bash_tool() { jq -cn --arg c "$1" '{type: "tool_use", name: "Bash", input: {command: $c}}'; }
# assistant MODEL SIDECHAIN TOOL...: a TOOL is a tool name or a tool_use object.
assistant() {
  local model="$1" sidechain="$2"
  shift 2
  printf '%s\n' "$@" | jq -cs --arg m "$model" --argjson s "$sidechain" -R '
    split("\n") | map(select(. != "") | . as $line | (try fromjson catch {type: "tool_use", name: $line}))
    | {type: "assistant", isSidechain: $s, message: {model: $m, content: .}}'
}
working_turn() {
  user_prompt
  assistant claude-opus-5 false Read Grep Edit Bash Edit Bash
}

# decide PAYLOAD_JSON: runs the hook. Sets DECISION to block, allow, or a
# description of an invalid result.
decide() {
  run_hook "$HOOK" <<<"$1"
  if [ "$STATUS" != 0 ]; then
    DECISION="exit status $STATUS"
  elif [ -z "$STDOUT" ]; then
    DECISION=allow
  elif [ "$(canonical_json "$STDOUT")" == "$(canonical_json "$BLOCK")" ]; then
    DECISION=block
  else
    DECISION="unexpected output: $STDOUT"
  fi
}
# decide_turn NAME LINES: writes LINES as a transcript and runs the hook on it.
decide_turn() {
  printf '%s\n' "$2" >"$WORK/$1.jsonl"
  decide "$(jq -cn --arg t "$WORK/$1.jsonl" '{transcript_path: $t}')"
}
log_text() { cat "$CLEAN_RECAP_LOG" 2>/dev/null; }

# Manifest wiring.
config="$PLUGIN_ROOT_DIR/hooks/claude-hooks.json"
expect_equal "one Stop entry, so a duplicated key cannot lose a hook" 1 "$(jq '.hooks.Stop | length' "$config")"
expect_equal "Stop takes no matcher" false "$(jq '.hooks.Stop[0] | has("matcher")' "$config")"
expect_equal "the Stop hook is a command" command "$(jq -r '.hooks.Stop[0].hooks[0].type' "$config")"
expect_equal "the Stop hook runs the script with bash" 'bash "${CLAUDE_PLUGIN_ROOT}/hooks/opus_5_reduce_output.sh"' \
  "$(jq -r '.hooks.Stop[0].hooks[0].command' "$config")"
expect_equal "the Stop hook timeout is 10 s" 10 "$(jq '.hooks.Stop[0].hooks[0].timeout' "$config")"
expect_equal "the script is executable" yes "$([ -x "$HOOK" ] && echo yes || echo no)"
# Codex documents no turn-end event, and Copilot's agentStop envelope is
# camelCase, so its stopHookActive loop guard would never trip.
expect_equal "no Codex hooks file" absent "$([ -e "$PLUGIN_ROOT_DIR/hooks/codex-hooks.json" ] && echo present || echo absent)"
expect_equal "no Copilot hooks file" absent "$([ -e "$PLUGIN_ROOT_DIR/hooks.json" ] && echo present || echo absent)"
expect_equal "the recap instruction has no em dash" absent "$([[ "$RECAP_INSTRUCTION" == *—* ]] && echo present || echo absent)"

# The gate.
decide_turn work "$(working_turn)"
expect_equal "a fresh turn of real work blocks" block "$DECISION"
expect_contains "a block is logged" BLOCK "$(log_text)"

decide_turn idle "$(user_prompt; assistant claude-opus-5 false)"
expect_equal "a turn with no tool calls skips" allow "$DECISION"
decide_turn read "$(user_prompt; assistant claude-opus-5 false Read Read Read Read Read Read Read Read)"
expect_equal "a read-only turn skips" allow "$DECISION"
decide_turn small "$(user_prompt; assistant claude-opus-5 false Edit Bash)"
expect_equal "a two-tool turn asks for a recap" block "$DECISION"

# The mutation gate.
rm -f "$CLEAN_RECAP_LOG"
decide_turn look "$(user_prompt 'which python is on PATH?'; assistant claude-opus-5 false "$(bash_tool 'which python3')")"
expect_equal "one read-only shell command skips" allow "$DECISION"
expect_contains "the skip is logged" "turn used no mutating tool" "$(log_text)"
decide_turn edit "$(user_prompt; assistant claude-opus-5 false "$(bash_tool 'rg todo')" Edit)"
expect_equal "a turn containing an edit blocks" block "$DECISION"
decide_turn rm "$(user_prompt; assistant claude-opus-5 false "$(bash_tool 'rm -rf /workspace/build')")"
expect_equal "a mutating shell command blocks" block "$DECISION"
for tool in Agent MultiEdit SendMessage Task; do
  decide_turn "$tool" "$(user_prompt; assistant claude-opus-5 false "$tool")"
  expect_equal "a turn using $tool blocks" block "$DECISION"
done

# A tool result is type "user" too. Mistaking it for a prompt would cut the
# turn at its first tool call, on either side of the mutation.
decide_turn chain "$(user_prompt; assistant claude-opus-5 false "$(bash_tool 'cat /workspace/notes.md')"; tool_result
  assistant claude-opus-5 false "$(bash_tool "git commit -m 'save the notes'")")"
expect_equal "a tool result does not truncate the turn (mutation last)" block "$DECISION"
decide_turn tail "$(user_prompt; assistant claude-opus-5 false "$(bash_tool "git commit -m 'save the notes'")"; tool_result
  assistant claude-opus-5 false "$(bash_tool 'git show --stat HEAD')")"
expect_equal "a tool result does not truncate the turn (mutation first)" block "$DECISION"

decide_turn skill "$(user_prompt; assistant claude-opus-5 false "$(bash_tool 'mkdir /workspace/out')" Skill; injected_prompt
  assistant claude-opus-5 false "$(bash_tool 'ls /workspace/out')")"
expect_equal "an injected prompt does not truncate the turn" block "$DECISION"

rm -f "$CLEAN_RECAP_LOG"
decide_turn orphan "$(assistant claude-opus-5 false "$(bash_tool 'ls /workspace')")"
expect_equal "a promptless transcript asks for a recap" block "$DECISION"
expect_contains "a promptless transcript is logged" "turn boundary unknown" "$(log_text)"

rm -f "$CLEAN_RECAP_LOG"
decide_turn garbage "not json"$'\n'"$(assistant claude-opus-5 false "$(bash_tool 'ls /workspace')")"$'\n'"{ also not json"
expect_equal "unparseable lines around the turn ask for a recap" block "$DECISION"
expect_contains "the unknown boundary is logged" "turn boundary unknown" "$(log_text)"

rm -f "$CLEAN_RECAP_LOG"
decide_turn rubble "not json"$'\n'"{ also not json"
expect_equal "a wholly unparseable transcript allows at the model gate" allow "$DECISION"
expect_contains "the model gate is logged" "model does not match" "$(log_text)"

decide_turn prior "$(user_prompt 'older turn'; assistant claude-opus-5 false Edit Write; user_prompt 'this turn'
  assistant claude-opus-5 false "$(bash_tool 'git status')")"
expect_equal "only the current turn is examined" allow "$DECISION"

# Shell command classification, one command per turn.
classify() {
  local expected="$1" command
  shift
  for command in "$@"; do
    decide_turn classify "$(user_prompt; assistant claude-opus-5 false "$(bash_tool "$command")")"
    expect_equal "classify: $command" "$expected" "$DECISION"
  done
}
classify allow \
  "which python3" "ls -la /workspace" "git status" "git log --oneline -20" "git diff HEAD" "gh pr view 12" \
  "rg --files-with-matches todo /workspace" "cat /workspace/a.txt /workspace/b.txt" "pytest -q 2>&1" \
  "python3 -c 'print(1 >= 0)'" "grep -n foo /workspace/x | head -5" "ps aux | grep node" \
  "python3 scripts/generate-plugin-manifests.py --check >/dev/null 2>&1" \
  "python3 scripts/generate-plugin-manifests.py --check > /dev/null" \
  "python3 scripts/generate-plugin-manifests.py --check >>/dev/null" \
  "python3 scripts/generate-plugin-manifests.py --check >> /dev/null" \
  "git rev-parse HEAD 2>/dev/null" "git -C /workspace/wt status" "git --no-pager log -5" \
  "gh -R owner/repo pr view 12" "cmd >&2" "git status && git diff"
classify block \
  "rm -rf /workspace/build" "mv /workspace/a /workspace/b" "cp /workspace/a /workspace/b" \
  "mkdir -p /workspace/out" "touch /workspace/marker" "install -m 755 bin/tool /workspace/bin/tool" \
  "ln -s /workspace/a /workspace/b" "sed -i 's/a/b/' /workspace/x" "echo hi | tee /workspace/x" \
  "echo hi > /workspace/x" "echo hi >> /workspace/x" "git commit -m 'wip'" "git push origin develop" \
  "git merge develop" "git rebase develop" "git reset --hard HEAD" "git checkout develop" \
  "git branch -D stale" "git worktree add /workspace/wt develop" "git worktree remove /workspace/wt" \
  "gh pr create --base develop" "gh pr merge 12" "sudo chmod 600 /workspace/key" "FOO=bar rm /workspace/x" \
  "git -C /workspace/wt push origin develop" "git -C . add -A" \
  "git -C /workspace/wt worktree remove --force /workspace/gone" "git -c user.name=x commit -m 'wip'" \
  "gh -R owner/repo pr create --base develop" "make &> /workspace/build.log" \
  "python3 gen.py 1> /workspace/out.txt" "make 2> /workspace/build.log" "env FOO=1 rm /workspace/x" \
  "command rm /workspace/x" "find /workspace -name '*.tmp' | xargs rm -f" \
  "git status && git commit -m x" "ls; rm /workspace/x" "cat /workspace/a || touch /workspace/a" \
  "check >/dev/null && rm -rf /workspace/d" "check >/dev/null; touch /workspace/x" \
  "check >/dev/null 2>&1 > /workspace/out"

# Loop guard.
rm -f "$CLEAN_RECAP_LOG"
printf '%s\n' "$(working_turn)" >"$WORK/guard.jsonl"
decide "$(jq -cn --arg t "$WORK/guard.jsonl" '{stop_hook_active: true, transcript_path: $t}')"
expect_equal "the second stop allows so the session can end" allow "$DECISION"
expect_contains "the stand-down is logged" "stand down" "$(log_text)"
decide "$(jq -cn --arg t "$WORK/guard.jsonl" '{transcript_path: $t}')"
expect_equal "an absent stop_hook_active still blocks" block "$DECISION"
decide "$(jq -cn --arg t "$WORK/guard.jsonl" '{stop_hook_active: "true", transcript_path: $t}')"
expect_equal "stop_hook_active as a string allows" allow "$DECISION"

# Malformed input.
decide '{}'
expect_equal "an empty payload allows" allow "$DECISION"
rm -f "$CLEAN_RECAP_LOG"
decide "$(jq -cn --arg t "$WORK/gone.jsonl" '{transcript_path: $t}')"
expect_equal "a missing transcript file allows" allow "$DECISION"
expect_contains "a missing transcript is logged" "no readable transcript_path" "$(log_text)"
decide "$(jq -cn --arg t "$WORK" '{transcript_path: $t}')"
expect_equal "a transcript path pointing at a directory allows" allow "$DECISION"
decide 'not json'
expect_equal "a non-JSON payload allows" allow "$DECISION"

# Model matching.
rm -f "$CLEAN_RECAP_LOG"
decide_turn sonnet "$(user_prompt; assistant claude-sonnet-4-5 false Read Edit Bash Edit Read Bash)"
expect_equal "an unmatched model allows" allow "$DECISION"
expect_contains "the unmatched model is logged" "model does not match" "$(log_text)"
decide_turn fable "$(user_prompt; assistant claude-fable-5-1 false Read Edit Bash Edit Read Bash)"
expect_equal "a fable model blocks" block "$DECISION"
decide_turn opus "$(user_prompt; assistant claude-opus-5 false Read Edit Bash Edit Read Bash)"
expect_equal "an opus 5 model blocks" block "$DECISION"
decide_turn side "$(user_prompt; assistant claude-opus-5 true Read Edit Bash Edit Read Bash)"
expect_equal "sidechain work does not count" allow "$DECISION"
rm -f "$CLEAN_RECAP_LOG"
decide_turn order "$(user_prompt 'older turn'; assistant claude-sonnet-5 false Read; user_prompt 'this turn'
  assistant claude-opus-5 false Read)"
expect_contains "the model read is the one that answered last" "model=claude-opus-5 -> allow" "$(log_text)"
rm -f "$CLEAN_RECAP_LOG"
decide_turn bare "$(user_prompt hi)"
expect_contains "no assistant reply leaves the model unknown" "model=- -> allow" "$(log_text)"

# Logging.
rm -f "$CLEAN_RECAP_LOG"
for _ in $(seq 80); do
  CLEAN_RECAP_LOG_MAX_BYTES=500 decide '{}'
done
expect_equal "the log stays near its size limit" yes "$([ "$(wc -c <"$CLEAN_RECAP_LOG")" -le 800 ] && echo yes || echo no)"
expect_equal "old lines are dropped" yes "$([ "$(grep -c '' "$CLEAN_RECAP_LOG")" -lt 80 ] && echo yes || echo no)"
expect_equal "every line is a decision or a rollover marker" 0 \
  "$(grep -vc -e 'no readable transcript_path' -e 'rolled over' "$CLEAN_RECAP_LOG")"
expect_contains "a rollover marker is written" "clean-recap.log rolled over; earlier lines were dropped" "$(log_text)"
expect_equal "log lines start with a timestamp" 0 "$(grep -vEc '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2} ' "$CLEAN_RECAP_LOG")"

rm -f "$CLEAN_RECAP_LOG"
CLEAN_RECAP_LOG_MAX_BYTES=1MB decide "$(jq -cn --arg t "$WORK/guard.jsonl" '{transcript_path: $t}')"
expect_equal "a malformed max bytes falls back to the default" block "$DECISION"
expect_contains "the malformed max bytes run is logged" BLOCK "$(log_text)"

rm -f "$CLEAN_RECAP_LOG"
CLEAN_RECAP_MODEL_PATTERN='opus-5(' decide "$(jq -cn --arg t "$WORK/guard.jsonl" '{transcript_path: $t}')"
expect_equal "a malformed model pattern falls back to the default" block "$DECISION"
expect_contains "the rejected pattern is logged" "CLEAN_RECAP_MODEL_PATTERN 'opus-5(' rejected (" "$(log_text)"
expect_contains "the fallback is logged" "-> using default 'opus-5|fable'" "$(log_text)"
expect_contains "the fallback run blocks" BLOCK "$(log_text)"

rm -f "$CLEAN_RECAP_LOG"
decide "$(jq -cn --arg t "$WORK/guard.jsonl" '{transcript_path: $t}')"
decide '{}'
expect_equal "every decision is logged, one line each" 2 "$(grep -c '' "$CLEAN_RECAP_LOG")"
expect_equal "the first line is the block" "fired  model=claude-opus-5 -> BLOCK (requesting recap)" "$(sed -n 1p "$CLEAN_RECAP_LOG" | cut -d' ' -f2-)"
expect_equal "the second line is the allow" "fired  no readable transcript_path -> allow" "$(sed -n 2p "$CLEAN_RECAP_LOG" | cut -d' ' -f2-)"

# The manifest command, run the way Claude Code runs it.
export CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT_DIR"
run_wiring claude "$(jq -r '.hooks.Stop[0].hooks[0].command' "$config")" <<<"$(jq -cn --arg t "$WORK/guard.jsonl" '{transcript_path: $t}')"
expect_equal "the manifest command exits 0" 0 "$STATUS"
expect_json "the manifest command blocks with the recap instruction" "$BLOCK" "$STDOUT"

finish
