#!/bin/bash
# Fails when a link or backticked skill path in SKILL.md or a reference
# does not resolve.

. "${BASH_SOURCE[0]%/*}/../lib.sh" "$@"

for file in "$skill" "${refs[@]}"; do
  [ -f "$file" ] || continue
  while IFS= read -r target; do
    [ -n "$(resolve "$file" "$target")" ] ||
      fail "$file" "link to $target does not resolve" "fix the path, or add the file"
  done < <(targets "$file")
done
finish
