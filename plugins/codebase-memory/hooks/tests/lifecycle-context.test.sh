#!/bin/bash
# Behavior tests for lifecycle_context. 

HOOKS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLUGIN_ROOT_DIR="$(dirname "$HOOKS_DIR")"
# shellcheck source=../../../../scripts/hook-test-assertions.sh
. "$PLUGIN_ROOT_DIR/../../scripts/hook-test-assertions.sh"

HOOK="$HOOKS_DIR/lifecycle_context.sh"
INSTRUCTIONS=$(jq -Rrs 'gsub("\\A\\s+|\\s+\\z"; "")' "$HOOKS_DIR/instructions.md")
GRAPH_MARKER=GRAPH-CONTEXT-MARKER
CLAUDE_AUGMENT='{"hookSpecificOutput": {"hookEventName": "x", "additionalContext": "GRAPH-CONTEXT-MARKER"}}'
COPILOT_AUGMENT='{"additionalContext": "GRAPH-CONTEXT-MARKER"}'
REMINDER='codebase-memory auto-indexing is off, so new checkouts and worktrees have no graph until indexed. Mention this to the user once, and suggest they run `codebase-memory-mcp config set auto_index true`. Do not run it yourself.'
HOOK_INPUT='{"session_id": "s-1"}'
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

# PATH without any real codebase-memory-mcp on it.
CLEAN_PATH=
IFS=: read -ra path_entries <<<"$PATH"
for entry in "${path_entries[@]}"; do
  [ -x "$entry/codebase-memory-mcp" ] || CLEAN_PATH="$CLEAN_PATH${CLEAN_PATH:+:}$entry"
done

# fake_hook HARNESS EVENT AUGMENT_JSON [CONFIG_SCRIPT [AUGMENT_DELAY [INSTALL]]]
# Runs the hook against a fake binary. Sets CONTEXT (the injected text),
# OUTPUT (stdout as canonical JSON), CALLS (argv of each call) and FORWARDED
# (the stdin hook-augment received).
fake_hook() {
  local harness="$1" event="$2" augment="$3" config="${4:-echo true}" delay="${5:-0}" install="${6:-yes}"
  local bin
  bin=$(mktemp -d "$WORK/bin.XXXXXX")
  if [ "$install" = yes ]; then
    printf '%s\n' '#!/bin/sh' \
      "echo \"\$*\" >> \"$bin/calls.log\"" \
      "if [ \"\$1\" = config ]; then $config; else cat > \"$bin/stdin\"; sleep $delay; printf '%s' '$augment'; fi" \
      >"$bin/codebase-memory-mcp"
    chmod +x "$bin/codebase-memory-mcp"
  fi
  PATH="$bin:$CLEAN_PATH" run_hook "$HOOK" --harness "$harness" --event "$event" <<<"$HOOK_INPUT"
  OUTPUT=$(canonical_json "$STDOUT")
  CONTEXT=$(jq -r '.hookSpecificOutput.additionalContext // .additionalContext' <<<"$STDOUT")
  CALLS=$(cat "$bin/calls.log" 2>/dev/null)
  FORWARDED=$(cat "$bin/stdin" 2>/dev/null)
}

for event in SessionStart SubagentStart; do
  fake_hook claude "$event" "$CLAUDE_AUGMENT"
  expect_equal "claude $event echoes the event" "$event" "$(jq -r .hookSpecificOutput.hookEventName <<<"$STDOUT")"
  expect_equal "claude $event joins instructions and graph context" "$INSTRUCTIONS"$'\n\n'"$GRAPH_MARKER" "$CONTEXT"
  expect_equal "claude $event exits 0" 0 "$STATUS"
done
expect_equal "hook-augment receives the hook input" "$HOOK_INPUT" "$FORWARDED"

fake_hook copilot SubagentStart "$COPILOT_AUGMENT"
expect_equal "copilot uses top-level additionalContext only" '["additionalContext"]' "$(jq -c keys <<<"$STDOUT")"
expect_equal "copilot joins instructions and graph context" "$INSTRUCTIONS"$'\n\n'"$GRAPH_MARKER" "$CONTEXT"
expect_equal "copilot asks hook-augment for its dialect" "hook-augment --event SubagentStart --dialect copilot" "$CALLS"

fake_hook claude SessionStart ""
expect_json "silent hook-augment still yields the instructions (claude)" \
  "$(jq -cn --arg t "$INSTRUCTIONS" '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: $t}}')" "$STDOUT"
fake_hook copilot SessionStart ""
expect_json "silent hook-augment still yields the instructions (copilot)" \
  "$(jq -cn --arg t "$INSTRUCTIONS" '{additionalContext: $t}')" "$STDOUT"

for harness in claude copilot; do
  if [ "$harness" = claude ]; then augment=$CLAUDE_AUGMENT; else augment=$COPILOT_AUGMENT; fi
  fake_hook "$harness" SessionStart "$augment" "echo false"
  expect_equal "$harness SessionStart reminds when auto_index is off" \
    "$INSTRUCTIONS"$'\n\n'"$GRAPH_MARKER"$'\n\n'"$REMINDER" "$CONTEXT"
  expect_contains "$harness SessionStart runs the auto_index check" "config get auto_index" "$CALLS"
done

fake_hook claude SessionStart "$CLAUDE_AUGMENT" "echo true"
expect_equal "no reminder when auto_index is on" "$INSTRUCTIONS"$'\n\n'"$GRAPH_MARKER" "$CONTEXT"
expect_contains "the check ran when auto_index is on" "config get auto_index" "$CALLS"

for failure in "non-zero exit|echo false; exit 1" "unexpected output|echo maybe" "timeout|exec sleep 30"; do
  name=${failure%%|*}
  start=$SECONDS
  fake_hook claude SessionStart "" "${failure#*|}"
  expect_equal "no reminder when the check fails ($name)" "$INSTRUCTIONS" "$CONTEXT"
  expect_contains "the check ran ($name)" "config get auto_index" "$CALLS"
  expect_equal "the hook stays inside its 5 s budget ($name)" yes "$([ $((SECONDS - start)) -le 5 ] && echo yes || echo no)"
done

fake_hook claude SessionStart "$CLAUDE_AUGMENT" "sleep 3; echo false" 3
expect_equal "the check runs concurrently with hook-augment" \
  "$INSTRUCTIONS"$'\n\n'"$GRAPH_MARKER"$'\n\n'"$REMINDER" "$CONTEXT"

fake_hook claude SessionStart "" "echo true" 0 no
expect_equal "missing binary still yields the instructions" "$INSTRUCTIONS" "$CONTEXT"
expect_equal "missing binary exits 0" 0 "$STATUS"
expect_equal "missing binary makes no calls" "" "$CALLS"

for harness in claude copilot; do
  if [ "$harness" = claude ]; then augment=$CLAUDE_AUGMENT; else augment=$COPILOT_AUGMENT; fi
  fake_hook "$harness" SubagentStart "$augment" "echo false"
  expect_equal "$harness SubagentStart never adds the reminder" "$INSTRUCTIONS"$'\n\n'"$GRAPH_MARKER" "$CONTEXT"
  expect_equal "$harness SubagentStart makes one call" 1 "$(grep -c '' <<<"$CALLS")"
  expect_equal "$harness SubagentStart calls hook-augment only" hook-augment "${CALLS%% *}"
done

run_hook "$HOOK" --harness codex --event SessionStart </dev/null
expect_equal "an unknown harness exits 0" 0 "$STATUS"
expect_equal "an unknown harness prints nothing" "" "$STDOUT"
expect_contains "an unknown harness is rejected" "invalid choice" "$STDERR"

# Each harness config runs the hook for both events.
bin="$WORK/wired-bin"
mkdir "$bin"
printf '#!/bin/sh\n[ "$1" = config ] && echo true\nexit 0\n' >"$bin/codebase-memory-mcp"
chmod +x "$bin/codebase-memory-mcp"
export PLUGIN_ROOT="$PLUGIN_ROOT_DIR" CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT_DIR"
for wiring in "claude hooks/claude-hooks.json SessionStart SubagentStart" "copilot hooks.json sessionStart subagentStart"; do
  read -r harness config session_event subagent_event <<<"$wiring"
  for event in "$session_event" "$subagent_event"; do
    count=0
    while IFS= read -r command; do
      count=$((count + 1))
      PATH="$bin:$CLEAN_PATH" run_wiring "$harness" "$command" <<<"$HOOK_INPUT"
      expect_equal "$config $event injects the instructions" "$INSTRUCTIONS" \
        "$(jq -r '.hookSpecificOutput.additionalContext // .additionalContext' <<<"$STDOUT")"
    done < <(wiring_commands "$harness" "$PLUGIN_ROOT_DIR/$config" "$event")
    expect_equal "$config wires one $event hook" 1 "$count"
    [ "$harness" = copilot ] || continue
    while IFS= read -r command; do
      PATH="$bin:$CLEAN_PATH" run_windows_wiring "$command" "$HOOKS_DIR" <<<"$HOOK_INPUT"
      expect_equal "$config $event Windows command injects the instructions" "$INSTRUCTIONS" \
        "$(jq -r '.additionalContext' <<<"$STDOUT")"
    done < <(windows_commands copilot "$PLUGIN_ROOT_DIR/$config" "$event")
  done
done

finish
