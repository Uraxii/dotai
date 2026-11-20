#!/bin/bash
# Fails when SKILL.md or a reference writes a skill path with a backslash.

. "${BASH_SOURCE[0]%/*}/../lib.sh" "$@"

for file in "$skill" "${refs[@]}"; do
  [ -f "$file" ] || continue
  while IFS=$'\t' read -r line text; do
    [[ "$text" =~ (scripts|references|playbooks|examples|assets)\\ ]] &&
      fail "$file" "line $line has a backslash path" "use / in skill paths"
  done < <(prose "$file")
done
finish
