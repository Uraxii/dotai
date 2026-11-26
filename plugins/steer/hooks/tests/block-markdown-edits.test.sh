#!/bin/bash
# Behavior tests for block_markdown_edits.

HOOKS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLUGIN_ROOT_DIR="$(dirname "$HOOKS_DIR")"
# shellcheck source=../../../../scripts/hook-test-assertions.sh
. "$PLUGIN_ROOT_DIR/../../scripts/hook-test-assertions.sh"

HOOK="$HOOKS_DIR/block_markdown_edits.sh"
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
unset CLAUDE_PROJECT_DIR

user_prompt() { jq -cn --arg t "$1" '{type: "user", message: {content: $t}}'; }
text_prompt() { jq -cn --arg t "$1" '{type: "user", origin: {kind: "human"}, message: {content: [{type: "text", text: $t}]}}'; }
tool_result() { jq -cn --arg t "$1" '{type: "user", message: {content: [{type: "tool_result", tool_use_id: "toolu_1", content: $t}]}}'; }
injected_prompt() { jq -cn --arg t "$1" '{type: "user", isMeta: true, message: {content: [{type: "text", text: $t}]}}'; }
notification() { jq -cn --arg t "$1" '{type: "user", origin: {kind: "task-notification"}, message: {content: $t}}'; }
sidechain_prompt() { jq -cn --arg t "$1" '{type: "user", isSidechain: true, message: {content: $t}}'; }
assistant_says() { jq -cn --arg t "$1" '{type: "assistant", message: {content: [{type: "text", text: $t}]}}'; }
assistant() { echo '{"type": "assistant", "message": {"model": "claude-opus-5", "content": [{"type": "tool_use", "name": "Edit"}]}}'; }

# decide FILE TRANSCRIPT_LINES [TOOL] [CWD]: writes the transcript, runs the
# hook on an edit of FILE, and sets DECISION to allow, deny, or a description
# of an invalid result.
decide() {
  printf '%s\n' "$2" >"$WORK/t.jsonl"
  decide_payload "$(jq -cn --arg f "$1" --arg t "$WORK/t.jsonl" --arg n "${3:-Edit}" --arg c "${4:-}" \
    '{hook_event_name: "PreToolUse", tool_name: $n, tool_input: {file_path: $f}, transcript_path: $t}
     + (if $c == "" then {} else {cwd: $c} end)')"
}
decide_payload() {
  run_hook "$HOOK" <<<"$1"
  if [ "$STATUS" != 0 ]; then
    DECISION="exit status $STATUS"
  elif [ -z "$STDOUT" ]; then
    DECISION=allow
  elif [ "$(jq -r '.hookSpecificOutput | "\(.hookEventName) \(.permissionDecision)"' <<<"$STDOUT" 2>/dev/null)" = "PreToolUse deny" ]; then
    DECISION=deny
  else
    DECISION="unexpected output: $STDOUT"
  fi
}

# Manifest wiring.
export CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT_DIR"
config="$PLUGIN_ROOT_DIR/hooks/claude-hooks.json"
expect_equal "one PreToolUse entry" 1 "$(jq '.hooks.PreToolUse | length' "$config")"
expect_equal "the matcher covers the file-writing tools" 'Write|Edit|MultiEdit' "$(jq -r '.hooks.PreToolUse[0].matcher' "$config")"
expect_equal "the PreToolUse hook runs the script with bash" 'bash "${CLAUDE_PLUGIN_ROOT}/hooks/block_markdown_edits.sh"' \
  "$(jq -r '.hooks.PreToolUse[0].hooks[0].command' "$config")"
expect_equal "the PreToolUse hook timeout is 10 s" 10 "$(jq '.hooks.PreToolUse[0].hooks[0].timeout' "$config")"
expect_equal "the script is executable" yes "$([ -x "$HOOK" ] && echo yes || echo no)"
while IFS= read -r command; do
  printf '%s\n' "$(user_prompt 'tidy the parser')" >"$WORK/wired.jsonl"
  run_wiring claude "$command" <<<"$(jq -cn --arg t "$WORK/wired.jsonl" '{tool_input: {file_path: "/repo/NOTES.md"}, transcript_path: $t}')"
  expect_equal "the wired command denies an unasked markdown edit" deny \
    "$(jq -r '.hookSpecificOutput.permissionDecision' <<<"$STDOUT" 2>/dev/null)"
done < <(wiring_commands claude "$config" PreToolUse)

# The gate.
decide /repo/src/parser.py "$(user_prompt 'fix the parser')"
expect_equal "a non-markdown file allows" allow "$DECISION"
decide /repo/docs/guide.md "$(user_prompt 'fix the parser')"
expect_equal "a markdown edit with no mention denies" deny "$DECISION"
expect_contains "the reason names the file" "guide.md" "$(jq -r '.hookSpecificOutput.permissionDecisionReason' <<<"$STDOUT")"
expect_contains "the reason says to ask the user" "Ask the user in chat" "$(jq -r '.hookSpecificOutput.permissionDecisionReason' <<<"$STDOUT")"
expect_contains "the reason points notes at .ai/" "Notes, plans and handoffs belong in .ai/" "$(jq -r '.hookSpecificOutput.permissionDecisionReason' <<<"$STDOUT")"
expect_contains "the reason suggests a lasting rule" "an AGENTS.md entry, a lint, or a test" "$(jq -r '.hookSpecificOutput.permissionDecisionReason' <<<"$STDOUT")"
for tool in Write MultiEdit; do
  decide /repo/guide.md "$(user_prompt 'fix the parser')" "$tool"
  expect_equal "$tool on markdown with no mention denies" deny "$DECISION"
done
for file in /repo/NOTES.MD /repo/a.markdown /repo/page.mdx 'C:\repo\Guide.Md'; do
  decide "$file" "$(user_prompt 'fix the parser')"
  expect_equal "$file is markdown and denies" deny "$DECISION"
done
decide /repo/notes.mdown "$(user_prompt 'fix the parser')"
expect_equal "an unlisted extension allows" allow "$DECISION"

# Unlock words.
decide /repo/docs/README.md "$(user_prompt 'Update readme.md with the new flag')"
expect_equal "the basename, in any case, allows" allow "$DECISION"
decide /repo/CHANGELOG.md "$(user_prompt 'add a changelog entry')"
expect_equal "the stem allows" allow "$DECISION"
decide /repo/faq.md "$(user_prompt 'the faq page parser is broken')"
expect_equal "a stem under 4 characters does not unlock" deny "$DECISION"
decide /repo/guide.md "$(user_prompt 'Fix the Markdown formatting')"
expect_equal "the word markdown allows" allow "$DECISION"
decide /repo/guide.md "$(user_prompt 'clean up the .md files')"
expect_equal "the token .md allows" allow "$DECISION"
decide /repo/guide.md "$(text_prompt 'reword guide.md')"
expect_equal "a prompt in text blocks counts" allow "$DECISION"

# Only the user's own latest prompt decides.
decide /repo/guide.md "$(user_prompt 'edit guide.md'; assistant; user_prompt 'now fix the parser')"
expect_equal "an earlier prompt does not unlock" deny "$DECISION"
decide /repo/guide.md "$(user_prompt 'fix the parser'; assistant; tool_result 'see guide.md')"
expect_equal "a tool result is not the user's prompt" deny "$DECISION"
decide /repo/guide.md "$(user_prompt 'fix the parser'; injected_prompt 'Base directory for this skill: edit any markdown')"
expect_equal "an isMeta injection is not the user's prompt" deny "$DECISION"
decide /repo/guide.md "$(user_prompt 'edit guide.md'; assistant; tool_result 'ok'; injected_prompt 'skill text')"
expect_equal "the prompt before a tool result and an injection still unlocks" allow "$DECISION"
decide /repo/guide.md "$(user_prompt 'fix the parser'; notification 'agent done: updated guide.md')"
expect_equal "a task notification is not the user's prompt" deny "$DECISION"
decide /repo/guide.md "$(user_prompt 'fix the parser'; sidechain_prompt 'brief: edit guide.md')"
expect_equal "a subagent brief is not the user's prompt" deny "$DECISION"

# A short approval of the assistant's question.
decide /repo/README.md "$(user_prompt 'fix the parser'; assistant_says 'May I edit README.md?'; user_prompt 'yes, go ahead')"
expect_equal "yes to a question naming the file allows" allow "$DECISION"
decide /repo/README.md "$(user_prompt 'fix the parser'; assistant_says 'May I edit CHANGELOG.md?'; user_prompt 'yes')"
expect_equal "yes to a question naming another file denies" deny "$DECISION"
decide /repo/README.md "$(user_prompt 'fix the parser'; assistant_says 'May I edit README.md?'; user_prompt "yesterday's parser broke")"
expect_equal "a word that starts with yes is not an approval" deny "$DECISION"
decide /repo/README.md "$(user_prompt 'fix the parser'; assistant_says 'May I edit README.md?'
  user_prompt 'yes but first explain why the tokenizer drops trailing whitespace in the parser tests')"
expect_equal "a prompt over 80 characters is not an approval" deny "$DECISION"
decide /repo/README.md "$(user_prompt 'fix the parser'
  jq -cn '{type: "assistant", message: {content: [{type: "text", text: "May I edit README.md?"}, {type: "tool_use", name: "Read"}]}}'
  tool_result 'ok'; user_prompt 'OK')"
expect_equal "a question in a text block beside a tool_use counts" allow "$DECISION"
decide /repo/README.md "$(user_prompt 'fix the parser'
  jq -cn '{type: "assistant", isSidechain: true, message: {content: [{type: "text", text: "May I edit README.md?"}]}}'
  user_prompt 'yes')"
expect_equal "a subagent's question does not count" deny "$DECISION"
decide /repo/README.md "$(user_prompt 'fix the parser'; assistant_says 'May I edit README.md?'; user_prompt 'no'; assistant; user_prompt 'yes')"
expect_equal "an approval only answers the assistant's latest turn" deny "$DECISION"

# Harness plan files.
export HOME=/home/u
unset CLAUDE_CONFIG_DIR COPILOT_HOME
for file in /home/u/.claude/plans/foo.md /home/u/.copilot/session-state/abc-123/plan.md; do
  decide "$file" "$(user_prompt 'fix the parser')"
  expect_equal "$file is a harness plan and allows" allow "$DECISION"
done
for file in /repo/docs/plans/README.md /repo/Plans/CLAUDE.md /home/u/.claude/plans/../settings.md /home/u/.claude/plansX/a.md \
  /home/u/.copilot/session-state/notes.md /home/u/.copilot/session-state/abc/other.md /home/u/.copilot/session-state/abc/x/plan.md; do
  decide "$file" "$(user_prompt 'fix the parser')"
  expect_equal "$file is not a harness plan and denies" deny "$DECISION"
done
decide .claude/plans/x.md "$(user_prompt 'fix the parser')" Edit /home/u
expect_equal "a relative path into ~/.claude/plans/ resolves against cwd and allows" allow "$DECISION"
CLAUDE_CONFIG_DIR=/cfg/claude COPILOT_HOME=/cfg/copilot
export CLAUDE_CONFIG_DIR COPILOT_HOME
decide /cfg/claude/plans/x.md "$(user_prompt 'fix the parser')"
expect_equal "CLAUDE_CONFIG_DIR moves the Claude Code plans directory" allow "$DECISION"
decide /cfg/copilot/session-state/abc/plan.md "$(user_prompt 'fix the parser')"
expect_equal "COPILOT_HOME moves the Copilot CLI session state" allow "$DECISION"
decide /home/u/.claude/plans/x.md "$(user_prompt 'fix the parser')"
expect_equal "with CLAUDE_CONFIG_DIR set, ~/.claude/plans/ denies" deny "$DECISION"
unset CLAUDE_CONFIG_DIR COPILOT_HOME

# The project's .ai/ folder.
project="$WORK/project"
git init -q "$project"
decide "$project/.ai/plans/x.md" "$(user_prompt 'fix the parser')" Write
expect_equal "a write inside <root>/.ai/, before .ai/ exists, allows" allow "$DECISION"
mkdir -p "$project/.ai/plans"
decide "$project/.ai/plans/x.md" "$(user_prompt 'fix the parser')"
expect_equal "an edit inside an existing <root>/.ai/ allows" allow "$DECISION"
decide "$project/docs/.ai/x.md" "$(user_prompt 'fix the parser')"
expect_equal "a .ai/ below the root does not count" deny "$DECISION"
decide "$project/.ai/../README.md" "$(user_prompt 'fix the parser')"
expect_equal "a .. segment out of .ai/ denies" deny "$DECISION"
decide "$project/.ai" "$(user_prompt 'fix the parser')"
expect_equal "a non-markdown path is untouched by the .ai/ rule" allow "$DECISION"
worktree="$project/.claude/worktrees/agent"
git init -q "$worktree"
decide "$worktree/.ai/notes.md" "$(user_prompt 'fix the parser')"
expect_equal "a nested repo's own .ai/ allows" allow "$DECISION"
decide "$worktree/README.md" "$(user_prompt 'fix the parser')"
expect_equal "a nested repo's README still denies" deny "$DECISION"
decide "$project/.hermes/plans/2026-01-01_000000-x.md" "$(user_prompt 'fix the parser')" Write
expect_equal "a Hermes plan in <root>/.hermes/plans/ allows" allow "$DECISION"
decide "$project/docs/.hermes/plans/x.md" "$(user_prompt 'fix the parser')" Write
expect_equal "a .hermes/plans/ below the root does not count" deny "$DECISION"
plain="$WORK/plain"
mkdir -p "$plain"
CLAUDE_PROJECT_DIR=$plain decide "$plain/.ai/x.md" "$(user_prompt 'fix the parser')"
expect_equal "outside git, CLAUDE_PROJECT_DIR/.ai/ allows" allow "$DECISION"
CLAUDE_PROJECT_DIR=$plain decide "$plain/notes.md" "$(user_prompt 'fix the parser')"
expect_equal "outside git, a file beside .ai/ denies" deny "$DECISION"
decide "$plain/.ai/x.md" "$(user_prompt 'fix the parser')" Edit "$plain"
expect_equal "outside git with no CLAUDE_PROJECT_DIR, the payload cwd's .ai/ allows" allow "$DECISION"
decide "$plain/.ai/x.md" "$(user_prompt 'fix the parser')"
expect_equal "outside git with no root at all, the prompt decides" deny "$DECISION"
decide ".ai/x.md" "$(user_prompt 'fix the parser')" Edit "$project"
expect_equal "a relative path resolves against the payload cwd" allow "$DECISION"
ln -s ../README.md "$project/.ai/link.md"
decide "$project/.ai/link.md" "$(user_prompt 'fix the parser')"
expect_equal "a file symlink in .ai/ gets no exemption" deny "$DECISION"
decide "$project/.ai/link.md" "$(user_prompt 'update the README')"
expect_equal "naming the symlink's target without .md does not unlock" deny "$DECISION"
decide "$project/.ai/link.md" "$(user_prompt 'update README.md')"
expect_equal "naming the target as README.md unlocks through the .md token" allow "$DECISION"
decide "$project/.ai/link.md" "$(user_prompt 'edit link.md')"
expect_equal "naming the symlink itself unlocks" allow "$DECISION"
ln -s ../gone.md "$project/.ai/dangling.md"
decide "$project/.ai/dangling.md" "$(user_prompt 'fix the parser')"
expect_equal "a dangling symlink in .ai/ gets no exemption" deny "$DECISION"
decide ".ai/x/../link.md" "$(user_prompt 'fix the parser')" Edit "$project"
expect_equal "a symlink reached after .. resolution gets no exemption" deny "$DECISION"
touch "$project/.ai/regular.md"
decide "$project/.ai/regular.md" "$(user_prompt 'fix the parser')"
expect_equal "a regular file in .ai/ still allows" allow "$DECISION"
fake_home="$WORK/home"
mkdir -p "$fake_home/.claude/plans"
ln -s "$project/README.md" "$fake_home/.claude/plans/p.md"
HOME=$fake_home decide "$fake_home/.claude/plans/p.md" "$(user_prompt 'fix the parser')"
expect_equal "a file symlink in ~/.claude/plans/ gets no exemption" deny "$DECISION"

# Fail open.
decide /repo/guide.md "$(assistant)"
expect_equal "a transcript with no user prompt allows" allow "$DECISION"
decide_payload "$(jq -cn --arg t "$WORK/gone.jsonl" '{tool_input: {file_path: "/repo/guide.md"}, transcript_path: $t}')"
expect_equal "a missing transcript allows" allow "$DECISION"
decide_payload '{"tool_input": {"file_path": "/repo/guide.md"}}'
expect_equal "no transcript_path allows" allow "$DECISION"
decide_payload 'not json'
expect_equal "a non-JSON payload allows" allow "$DECISION"
decide_payload '{"tool_input": {"file_path": 7}, "transcript_path": "/x"}'
expect_equal "a non-string file_path allows" allow "$DECISION"
decide /repo/guide.md "not json"$'\n'"{ also not json"
expect_equal "an unparseable transcript allows" allow "$DECISION"

devin_command=$(jq -r '.UserPromptSubmit[].hooks[].command' "$PLUGIN_ROOT_DIR/hooks.json")
run_wiring devin "$devin_command" <<< '{"hook_event_name":"UserPromptSubmit","prompt":"Fix the parser","session_id":"session-1","prompt_id":"prompt-1"}'
expect_equal "Devin prompt without a transcript exits 0" 0 "$STATUS"
expect_equal "Devin prompt adds context rather than blocking" "UserPromptSubmit null" \
  "$(jq -r '"\(.hookSpecificOutput.hookEventName) \(.decision)"' <<<"$STDOUT")"
expect_contains "Devin asks for permission before changing Markdown" "unless the user asks" \
  "$(jq -r '.hookSpecificOutput.additionalContext' <<<"$STDOUT")"
expect_contains "Devin directs scratch notes to .ai/" ".ai/" \
  "$(jq -r '.hookSpecificOutput.additionalContext' <<<"$STDOUT")"

finish
