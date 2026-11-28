#!/bin/bash
# Checks each file whose closed frontmatter has `shape: playbook` or
# `shape: router`, at the top level or under `metadata:`. Other files are
# skipped. references/playbook-building-blocks.md states the same rules.
# - playbook: fails with no Reply label. Warns with no stop predicate, on a
#   loop with no limit, and on more than 10 numbered steps.
# - router: fails with no Default label, and on a list item that links to a
#   .md file that does not exist.

. "${BASH_SOURCE[0]%/*}/../lib.sh" "$@"

shape_of() {
  awk '{ sub(/\r$/, "") } NR == 1 { if (!/^---$/) exit; next } /^---$/ { closed = 1; exit }
    /^[^ \t]/ { meta = /^metadata:/ }
    found == "" && (/^shape:/ || meta && /^[ \t]+shape:/) {
      sub(/^[ \t]*shape:[ \t]*/, ""); sub(/[ \t]+#.*/, ""); gsub(/["'\'' \t]/, ""); found = tolower($0) }
    END { if (closed) print found }' "$1"
}

# True when a line of the text on standard input starts with the label: after
# optional blockquote markers and an optional list or heading marker, in
# optional bold, with a colon inside or outside the bold. A label with no
# colon must end its line.
has_label() {
  grep -qiE "^[[:space:]]*(>[[:space:]]*)*(([-*+]|[0-9]+\.)[[:space:]]+|#{1,6}[[:space:]]+)?(\*\*|__)?($1)(\*\*|__)?(:|[[:space:]]*$)"
}

# LINE<TAB>TEXT for each list item or paragraph of FILE, with its wrapped
# lines joined. Headings are left out.
items() {
  prose "$1" | awk '
    function flush() { if (text != "") print start "\t" text; text = "" }
    { body = $0; sub(/^[^\t]*\t/, "", body) }
    body ~ /^[ \t]*$/ || body ~ /^[ \t]*#/ { flush(); next }
    text == "" || body ~ /^[ \t]*([-*+]|[0-9]+\.)[ \t]/ { flush(); start = $0; sub(/\t.*/, "", start); text = body; next }
    { sub(/^[ \t]+/, "", body); text = text " " body }
    END { flush() }'
}

stop_words='stop|stops|done|exit|exits|finish|finished|complete|completed|end|ends'
loop_words='repeat|retry|retries|loop|iterate|go back|keep trying'
count='([0-9]+|<[^>]+>|one|two|three|four|five|six|seven|eight|nine|ten)'
limit="(at most|no more than|up to|max|maximum|maximum of) $count([^a-z]|$)|(^|[^a-z])$count (times|rounds|tries|attempts)"
limit="$limit|(^|[^a-z])(once|twice)([[:space:]]+(more|again))?[[:space:]]*([.,;:)]|$)"
# "until" alone is a loop, except after a negation in the same clause (a
# gate: "do not merge until the review passes") or at the end of a clause
# that names a step (a hold: "keep it until step 6").
not_loop_until="(^|[^a-z])(do not|don't|don’t|never|must not)[[:space:]].*until([^a-z]|$)|until (step|steps) $count[[:space:]]*$"

# until_loop: true when a clause of the text on standard input has an "until"
# that is a loop. Clauses end at a comma, a semicolon, " and ", or the end of
# a sentence; a dot inside a word, as in README.md, ends nothing.
until_loop() {
  awk '{ gsub(/[,;]|[.!?]([ \t]|$)|[ \t][Aa][Nn][Dd][ \t]/, "\n"); print }' |
    grep -iE "(^|[^a-z-])until([^a-z-]|$)" | grep -viE "$not_loop_until" | grep -q .
}

for file in "$skill" "${refs[@]}"; do
  [ -f "$file" ] || continue
  shape=$(shape_of "$file")
  [ -n "$shape" ] || continue
  text=$(prose "$file" | cut -f2-)
  case $shape in
    playbook)
      has_label reply <<<"$text" ||
        fail "$file" "playbook has no Reply label" "end with '**Reply:** <items>.'"
      tr '\n' ' ' <<<"$text" | sed -E 's/\*\*|__//g' |
        grep -qiE "(^|[^a-z])($stop_words)[[:space:]]+(when|if|once|after)([^a-z]|$)" ||
        warn "$file" "playbook has no stop predicate" "add 'Done when <check>.'"
      steps=$(grep -cE '^[0-9]+\.[[:space:]]' <<<"$text")
      [ "$steps" -le 10 ] || warn "$file" "playbook has $steps steps, over 10" "split it, or move detail to a reference"
      while IFS=$'\t' read -r line body; do
        body=$(sed -E 's/"[^"]*"//g' <<<"$body") # quoted user words are not steps
        # A hyphen joins a name such as diagnose-loop, which is not a loop.
        # "at least once" and "all at once" set no limit.
        { grep -qiE "(^|[^a-z-])($loop_words)([^a-z-]|$)" <<<"$body" || until_loop <<<"$body"; } &&
          ! sed -E 's/[Aa][Tt] [Ll][Ee][Aa][Ss][Tt] [Oo][Nn][Cc][Ee]|[Aa][Ll][Ll] [Aa][Tt] [Oo][Nn][Cc][Ee]//g' <<<"$body" | grep -qiE "$limit" &&
          warn "$file" "line $line has a loop with no limit" "add 'at most <N> times', and the route after the limit"
      done < <(items "$file")
      ;;
    router)
      has_label 'default( route)?' <<<"$text" ||
        fail "$file" "router has no Default label" "add 'Default: <route for a request that matches no route>.'"
      while IFS=$'\t' read -r line body; do
        [[ "$body" =~ ^[[:space:]]*([-*+]|[0-9]+\.)[[:space:]] ]] || continue
        while IFS= read -r target; do
          [ -n "$(resolve "$file" "$target")" ] ||
            fail "$file" "line $line routes to $target, which does not exist" "fix the path, or add the procedure file"
        done < <(text_targets <<<"$body" | grep -E '\.md$')
      done < <(items "$file")
      ;;
    *) warn "$file" "shape '$shape' is not playbook or router" "use 'shape: playbook' or 'shape: router'" ;;
  esac
done
finish
