#!/bin/bash
# Checks each file whose frontmatter has `shape: playbook` or `shape: router`,
# at the top level or under metadata. Other files are skipped.
# - playbook: fails with no stop predicate or no Reply line. Warns on a loop
#   line with no limit, and on more than 10 numbered steps.
# - router: fails on a route line whose .md target does not exist, and when
#   no line names a default route.

. "${BASH_SOURCE[0]%/*}/../lib.sh" "$@"

shape_of() {
  awk '{ sub(/\r$/, "") } NR == 1 { if (!/^---$/) exit; next } /^---$/ { exit }
    /^[ \t]*shape:/ { sub(/^[ \t]*shape:[ \t]*/, ""); gsub(/["'\'' \t]/, ""); print; exit }' "$1"
}

for file in "$skill" "${refs[@]}"; do
  [ -f "$file" ] || continue
  shape=$(shape_of "$file")
  [ -n "$shape" ] || continue
  text=$(prose "$file" | cut -f2-)
  case $shape in
    playbook)
      grep -qiE '(^|[^a-z])(stop|done|exit|finish) (when|if|once|after)([^a-z]|$)' <<<"$text" ||
        fail "$file" "playbook has no stop predicate" "add 'Done when <check>.'"
      grep -qiE '^[[:space:]]*(\*\*)?reply:' <<<"$text" ||
        fail "$file" "playbook has no Reply line" "end with '**Reply:** <items>.'"
      steps=$(grep -cE '^[0-9]+\.[[:space:]]' <<<"$text")
      [ "$steps" -le 10 ] || warn "$file" "playbook has $steps steps, over 10" "split it, or move detail to a reference"
      while IFS=$'\t' read -r line body; do
        body=$(sed -E 's/"[^"]*"//g' <<<"$body") # quoted user words are not steps
        # A hyphen joins a name such as diagnose-loop, which is not a loop.
        grep -qiE '(^|[^a-z-])(repeat|retry|retries|loop|iterate|until|again)([^a-z-]|$)' <<<"$body" &&
          ! sed -E 's/^[[:space:]]*([0-9]+\.|[-*+])[[:space:]]//' <<<"$body" | grep -qiE '[0-9]|at most|up to|no more than|max' &&
          warn "$file" "line $line has a loop with no limit" "add 'at most <N> times', and the route after the limit"
      done < <(prose "$file")
      ;;
    router)
      grep -qiE '(^|[^a-z])default([^a-z]|$)' <<<"$text" ||
        fail "$file" "router has no default route" "add 'Default: <route for a request that matches no route>.'"
      while IFS=$'\t' read -r line body; do
        [[ "$body" =~ ^[[:space:]]*([-*+]|[0-9]+\.)[[:space:]] ]] || continue
        while IFS= read -r target; do
          [ -n "$(resolve "$file" "$target")" ] ||
            fail "$file" "line $line routes to $target, which does not exist" "fix the path, or add the procedure file"
        done < <(grep -oE '\]\(<?[^)[:space:]>]+\.md(#[^)]*)?>?\)|`[^`[:space:]]+\.md`' <<<"$body" |
          sed -E 's/^\]\(<?//; s/>?\)$//; s/#.*//; s/`//g' | grep -vE '^[a-z]+:|^/|[<>*{}$]')
      done < <(prose "$file")
      ;;
    *) warn "$file" "shape '$shape' is not playbook or router" "use 'shape: playbook' or 'shape: router'" ;;
  esac
done
finish
