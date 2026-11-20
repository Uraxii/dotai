#!/bin/bash
# Fails when the description has an XML tag, which can inject instructions.

. "${BASH_SOURCE[0]%/*}/../lib.sh" "$@"

skill_description | grep -qE '</?[A-Za-z][^>]*>' &&
  fail "$skill" "description has an XML tag, which can inject instructions" "use plain text"
finish
