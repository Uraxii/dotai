#!/bin/bash
# Warns when a reference has more than 100 lines and no table of
# contents near the top.

. "${BASH_SOURCE[0]%/*}/../lib.sh" "$@"

for ref in "${refs[@]}"; do
  lines=$(wc -l <"$ref" | tr -d " ")
  [ "$lines" -gt 100 ] && ! head -n 40 "$ref" | grep -qiE '^#+ .*contents|\]\(#' &&
    warn "$ref" "file has $lines lines and no table of contents near the top" "add a contents list after the title"
done
finish
