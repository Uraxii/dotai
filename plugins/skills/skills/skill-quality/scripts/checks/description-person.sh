#!/bin/bash
# Warns when the description is not third person.

. "${BASH_SOURCE[0]%/*}/../lib.sh" "$@"

skill_description | grep -qiE '^(use|i |you|this skill)' &&
  warn "$skill" "description is not third person" "start with what the skill does, such as 'Reviews ...'"
finish
