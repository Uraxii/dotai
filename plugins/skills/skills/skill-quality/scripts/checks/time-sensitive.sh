#!/bin/bash
# Warns on lines in SKILL.md or a reference that may hold a fact that decays.

. "${BASH_SOURCE[0]%/*}/../lib.sh" "$@"

for file in "$skill" "${refs[@]}"; do
  [ -f "$file" ] || continue
  while IFS=$'\t' read -r line text; do
    grep -qiE '(^|[^a-z])(as of|currently|new in)([^a-z]|$)|(^|[^0-9])20[0-9]{2}([^0-9]|$)' <<<"$text" &&
      warn "$file" "line $line may hold a fact that decays: ${text:0:80}" "query the source at use, name an update rule, or cut the claim"
  done < <(prose "$file")
done
finish
