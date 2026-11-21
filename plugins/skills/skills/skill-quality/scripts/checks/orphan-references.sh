#!/bin/bash
# Fails when no link from SKILL.md, or from a linked reference that is
# not a README.md, reaches a reference file. License and notice files are
# for people, not the agent, so nothing has to link them.

. "${BASH_SOURCE[0]%/*}/../lib.sh" "$@"

seen=$(reached)
for ref in "${refs[@]}"; do
  case ${ref#"$dir"/} in
    */licenses/* | */LICENSE* | */NOTICE* | */COPYING*) continue ;;
  esac
  grep -qF "$ref	" <<<"$seen" ||
    fail "$ref" "no link from SKILL.md or a linked reference reaches this file" "link it from SKILL.md with when to read it, or delete it"
done
finish
