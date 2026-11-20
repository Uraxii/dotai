#!/bin/bash
# Fails when SKILL.md, its name, or its description is missing.

. "${BASH_SOURCE[0]%/*}/../lib.sh" "$@"

if [ ! -f "$skill" ]; then
  fail "$skill" "SKILL.md is missing" "add SKILL.md with name and description frontmatter"
else
  [ -n "$(skill_name)" ] || fail "$skill" "frontmatter has no name" "add 'name: <directory name>'"
  [ -n "$(skill_description)" ] || fail "$skill" "frontmatter has no description" "add a description that says what the skill does and when to use it"
fi
finish
