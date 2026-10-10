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
printf '#!/bin/bash\nexit 1\n' > "$WORKDIR/portal-stub"
chmod +x "$WORKDIR/portal-stub"
ln -s "$WORKDIR/portal-stub" "$WORKDIR/bin/npx"
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
  PATH="$WORKDIR/bin" PORTAL_CLI_BIN="$portal_bin" SHUNT_MIN_LINES="$chunk" \
    "$BASH_BIN" "$SCRIPT_DIR/../hooks/$hook" --harness "$harness" <<< "$1"
}

for harness in claude codex copilot; do
  for hook in check-file-size check-bash-read; do
    for portal in absent path override override-with-args; do
      portal_bin=""
      rm -f "$WORKDIR/bin/portal-cli"
      case "$portal" in
        path) ln -s "$WORKDIR/portal-stub" "$WORKDIR/bin/portal-cli" ;;
        override) portal_bin="$WORKDIR/portal-stub" ;;
        override-with-args) portal_bin="$WORKDIR/portal-stub --instance test" ;;
      esac
      for chunk in 350 200; do
        args=$(jq -cn --arg file "$WORKDIR/full.txt" \
          '{file_path: $file, path: $file, command: ("cat " + $file)}')
        input=$(jq -cn --argjson args "$args" \
          '{tool_input: $args, toolArgs: $args}')
        result=$(invoke "$input")
        reason=$(jq -r '.permissionDecisionReason // .hookSpecificOutput.permissionDecisionReason' <<< "$result")
        label="$harness/$hook/$portal/$chunk"
        check "$label/deny" deny "$(jq -r '.permissionDecision // .hookSpecificOutput.permissionDecision' <<< "$result")"
        check "$label/guidance" true "$(jq -n --arg r "$reason" --arg chunk "$chunk" \
          '$r | startswith("File is 480 lines.") and contains("chunks of at most " + $chunk + " lines") and contains("full file") and contains("sed -n '\''START,ENDp'\'' FILE") and contains("grep")')"
        expected=true
        [ "$portal" = absent ] && expected=false
        check "$label/delegation" "$expected" "$(jq -n --arg r "$reason" '$r | contains("/bulk-reader")')"
        if [ "$hook" = check-file-size ] && [ "$harness" != codex ]; then
          if [ "$harness" = copilot ]; then
            check "$label/view-params" true "$(jq -n --arg r "$reason" --arg chunk "$chunk" '$r | contains("view_range [start, end]") and contains("[1, " + $chunk + "]") and (contains("offset") | not)')"
            args=$(jq -c --argjson chunk "$chunk" '. + {view_range: [1, $chunk]}' <<< "$args")
          else
            check "$label/read-params" true "$(jq -n --arg r "$reason" --arg chunk "$chunk" '$r | contains("offset=1, limit=" + $chunk)')"
            args=$(jq -c --argjson chunk "$chunk" '. + {offset: 1, limit: $chunk}' <<< "$args")
          fi
          input=$(jq -cn --argjson args "$args" '{tool_input: $args, toolArgs: $args}')
          check "$label/native-chunk-allowed" "" "$(invoke "$input")"
        fi
        command="sed -n '1,${chunk}p' $WORKDIR/full.txt"
        input=$(jq -cn --arg cmd "$command" '{tool_input: {command: $cmd}, toolArgs: {command: $cmd}}')
        saved_hook="$hook"
        hook=check-bash-read
        check "$label/bash-chunk-allowed" "" "$(invoke "$input")"
        hook="$saved_hook"
      done
    done
  done
done

sed -n '1,350p' "$WORKDIR/full.txt" > "$WORKDIR/chunks.txt"
sed -n '351,480p' "$WORKDIR/full.txt" >> "$WORKDIR/chunks.txt"
check "sed-chunks-read-full-file" "$(cat "$WORKDIR/full.txt")" "$(cat "$WORKDIR/chunks.txt")"
printf '## %d %d\n' "$PASSED" "$FAILED"
[ "$FAILED" -eq 0 ]
