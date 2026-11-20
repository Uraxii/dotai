#!/bin/bash
# Runs every check in checks/ on one skill directory. Each check prints its
# FAIL and WARN lines with a fix, and exits 1 on a FAIL. Exits 1 if any did.
#
# Usage: lint-skills.sh SKILL_DIR
# To run one check: checks/NAME.sh SKILL_DIR

[ -d "${1:-}" ] || { echo "usage: lint-skills.sh SKILL_DIR" >&2; exit 2; }
checks="${BASH_SOURCE[0]%/*}/checks"
status=0
output=
for check in "$checks"/*.sh; do
  out=$(bash "$check" "$1") || status=1
  [ -n "$out" ] && printf '%s\n' "$out" && output="$output$out
"
done
printf 'lint-skills.sh: %s: %d failed, %d warnings\n' "$(cd "$1" && pwd)" \
  "$(grep -c '^FAIL' <<<"$output")" "$(grep -c '^WARN' <<<"$output")"
exit "$status"
