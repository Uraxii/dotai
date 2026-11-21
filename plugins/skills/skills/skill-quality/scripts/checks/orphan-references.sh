#!/bin/bash
# Fails when no link from SKILL.md, or from a linked reference that is
# not a README.md, reaches a reference file. License and notice files are
# for people, not the agent, so nothing has to link them.

. "${BASH_SOURCE[0]%/*}/../lib.sh" "$@"

seen=$(reached)
for ref in "${refs[@]}"; do
  name=$(tr '[:upper:]' '[:lower:]' <<<"${ref##*/}")
  case $name in license | license[.-]* | notice | notice[.-]* | copying | copying[.-]*) continue ;; esac
  case /${ref#"$dir"/} in */licenses/*) continue ;; esac
  grep -qF "$ref	" <<<"$seen" ||
    fail "$ref" "no link from SKILL.md or a linked reference reaches this file" "link it from SKILL.md with when to read it, or delete it"
done
finish
