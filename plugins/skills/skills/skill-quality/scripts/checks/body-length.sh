#!/bin/bash
# Fails when the SKILL.md body is over 5,000 words. Warns when it is over
# 500 lines.

. "${BASH_SOURCE[0]%/*}/../lib.sh" "$@"

if [ -f "$skill" ]; then
  words=$(prose "$skill" | cut -f2- | wc -w | tr -d " ")
  [ "$words" -le 5000 ] || fail "$skill" "body is $words words, over 5,000" "cut, split, or move detail to references"
  lines=$(awk 'NR == 1 && /^---\r?$/ { front = 1; next } front { if (/^---\r?$/) front = 0; next } { n++ } END { print n + 0 }' "$skill")
  [ "$lines" -le 500 ] || warn "$skill" "body is $lines lines, over 500" "move detail to references"
fi
finish
