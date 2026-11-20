#!/bin/bash
# Fails when no link from SKILL.md, or from a linked reference that is
# not a README.md, reaches a reference file.

. "${BASH_SOURCE[0]%/*}/../lib.sh" "$@"

seen=$(reached)
for ref in "${refs[@]}"; do
  grep -qF "$ref	" <<<"$seen" ||
    fail "$ref" "no link from SKILL.md or a linked reference reaches this file" "link it from SKILL.md with when to read it, or delete it"
done
finish
