#!/bin/bash
# Fails when the SKILL.md body is over 5,000 words.

. "${BASH_SOURCE[0]%/*}/../lib.sh" "$@"

if [ -f "$skill" ]; then
  words=$(prose "$skill" | cut -f2- | wc -w | tr -d " ")
  [ "$words" -le 5000 ] || fail "$skill" "body is $words words, over 5,000" "cut, split, or move detail to references"
fi
finish
