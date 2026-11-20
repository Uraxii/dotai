#!/bin/bash
# Warns when the description does not say when to use the skill.

. "${BASH_SOURCE[0]%/*}/../lib.sh" "$@"

description=$(skill_description)
[ -z "$description" ] || grep -qiE '(^|[^a-z])(when|whenever|before|after|use for|use to|triggers?)([^a-z]|$)' <<<"$description" ||
  warn "$skill" "description does not say when to use the skill" "add 'Use when ...' with discovery keywords"
finish
