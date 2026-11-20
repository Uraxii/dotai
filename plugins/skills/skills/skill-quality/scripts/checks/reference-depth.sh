#!/bin/bash
# Warns when a reference is more than one link from SKILL.md, because
# agents may read a nested reference only in part.

. "${BASH_SOURCE[0]%/*}/../lib.sh" "$@"

seen=$(reached)
for ref in "${refs[@]}"; do
  depth=$(awk -F'\t' -v p="$ref" '$1 == p { print $2; exit }' <<<"$seen")
  [ -n "$depth" ] && [ "$depth" -gt 1 ] &&
    warn "$ref" "this file is $depth links from SKILL.md, so agents may read it only in part" "link it directly from SKILL.md"
done
finish
