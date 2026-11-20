#!/bin/bash
# Fails when the description is over 1,024 characters.

. "${BASH_SOURCE[0]%/*}/../lib.sh" "$@"

description=$(skill_description)
[ "${#description}" -le 1024 ] || fail "$skill" "description is ${#description} characters, over 1,024" "keep only capability and routing"
finish
