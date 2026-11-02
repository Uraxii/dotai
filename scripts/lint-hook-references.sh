#!/bin/bash
# Checks that every plugin hook manifest names hook files that exist, reads
# the plugin root through the variable its harness sets, and gives Copilot a
# PowerShell command that works on Windows.
#
# Usage: scripts/lint-hook-references.sh [--root DIR]
# DIR holds plugins/ and defaults to this checkout. Needs bash and jq.

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
[ "$1" = --root ] && root=$(cd "$2" && pwd)
checked=0
failed=0

fail() {
  printf 'FAIL  %s %s %s: %s\n      fix: %s\n' "${manifest#"$root"/}" "$1" "$2" "$3" "$4"
  failed=$((failed + 1))
}

# check EVENT FIELD COMMAND, with $plugin, $manifest and $allowed set.
# allowed is the root variable this harness sets, as the command must spell it.
check() {
  local event="$1" field="$2" command="$3" ref name
  checked=$((checked + 1))
  while read -r ref; do
    [ -z "$ref" ] && continue
    if [ "$field" = powershell ]; then
      [ "$ref" = '$env:PLUGIN_ROOT' ] && continue
      fail "$event" "$field" "reads the plugin root as $ref, which PowerShell treats as its own unset variable" \
        "write \$env:PLUGIN_ROOT"
    else
      name=${ref#\$}; name=${name#\{}; name=${name%\}}
      [[ " $allowed " == *" $name "* ]] && continue
      fail "$event" "$field" "reads the plugin root as $ref, which this harness does not set" \
        "use \${${allowed%% *}}"
    fi
  done < <(grep -oE '\$(\{[A-Za-z_:]+\}|env:[A-Za-z_]+|[A-Za-z_]+)' <<<"$command" | grep PLUGIN_ROOT)

  while read -r name; do
    [ -z "$name" ] && continue
    [ -e "$plugin/hooks/$name" ] && continue
    fail "$event" "$field" "names hooks/$name, which $plugin_name does not have" \
      "point it at a file in ${plugin#"$root"/}/hooks/"
  done < <({
    grep -oE 'PLUGIN_ROOT\}?[/\]hooks[/\][A-Za-z0-9._-]+' <<<"$command"
    grep -oE 'run-hook\.cmd"? +[^ ;"]+' <<<"$command"
  } | sed -E 's/.*[/\ ]//')

  # A command that starts with the script path runs it directly, so the
  # script needs its executable bit. Windows has no such bit.
  local direct='^"?\$\{?[A-Z_]*PLUGIN_ROOT\}?/hooks/([A-Za-z0-9._-]+)'
  if [[ "$field" = command || "$field" = bash ]] && [[ "$command" =~ $direct ]]; then
    name=${BASH_REMATCH[1]}
    [ -e "$plugin/hooks/$name" ] && [ ! -x "$plugin/hooks/$name" ] &&
      fail "$event" "$field" "runs hooks/$name directly, but it is not executable" \
        "git update-index --chmod=+x ${plugin#"$root"/}/hooks/$name, or run it with bash"
  fi

  if [ "$field" = powershell ] && [[ "$command" != *'; exit $LASTEXITCODE' ]]; then
    fail "$event" "$field" "does not end with '; exit \$LASTEXITCODE', so Copilot never sees the hook's exit status" \
      "append '; exit \$LASTEXITCODE'"
  fi
}

for manifest in "$root"/plugins/*/hooks.json "$root"/plugins/*/hooks/*.json; do
  [ -e "$manifest" ] || continue
  plugin_name=${manifest#"$root"/plugins/}
  plugin_name=${plugin_name%%/*}
  plugin=$root/plugins/$plugin_name
  case "${manifest#"$plugin"/}" in
    hooks.json) allowed=PLUGIN_ROOT ;;
    hooks/claude-hooks.json | hooks/hooks.json) allowed=CLAUDE_PLUGIN_ROOT ;;
    # Codex sets both; pstack's script reads CLAUDE_PLUGIN_ROOT under Codex.
    hooks/codex-hooks.json) allowed="PLUGIN_ROOT CLAUDE_PLUGIN_ROOT" ;;
    hooks/copilot-hooks.json) allowed=COPILOT_PLUGIN_ROOT ;;
    *)
      fail - - "is not a hook manifest name this lint knows" "rename it, or teach scripts/lint-hook-references.sh its harness"
      continue
      ;;
  esac
  if ! jq empty "$manifest" 2>/dev/null; then
    fail - - "is not valid JSON" "run jq . on it to find the syntax error"
    continue
  fi

  while IFS=$'\t' read -r event field command; do
    check "$event" "$field" "$command"
  done < <(jq -r '.hooks | to_entries[] | .key as $e | .value[] | (.hooks // [.])[]
    | to_entries[] | select(.key | IN("command", "bash", "powershell", "commandWindows"))
    | "\($e)\t\(.key)\t\(.value)"' "$manifest")

  if [ "${manifest#"$plugin"/}" = hooks.json ]; then
    while IFS=$'\t' read -r event has missing; do
      fail "$event" "$missing" "is missing beside $has; Copilot runs bash on Linux and macOS, powershell on Windows" \
        "add a $missing command for the same hook"
    done < <(jq -r '.hooks | to_entries[] | .key as $e | .value[]
      | select(has("bash") != has("powershell"))
      | if has("bash") then "\($e)\tbash\tpowershell" else "\($e)\tpowershell\tbash" end' "$manifest")
  fi
done

printf 'lint-hook-references.sh: %d commands checked, %d failed\n' "$checked" "$failed"
[ "$failed" -eq 0 ]
