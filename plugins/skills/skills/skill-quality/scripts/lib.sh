# Shared by every script in checks/. Source it with the skill directory:
#   . "${BASH_SOURCE[0]%/*}/../lib.sh" "$@"
# It sets dir, skill (SKILL.md) and refs (the .md files under references/,
# playbooks/ and examples/). A check reports with fail or warn, then calls
# finish, which exits 1 if it failed.

[ -d "${1:-}" ] || { echo "usage: ${0##*/} SKILL_DIR" >&2; exit 2; }
dir=$(cd "$1" && pwd)
skill="$dir/SKILL.md"
failed=0

refs=()
while IFS= read -r ref; do refs+=("$ref"); done < <(
  find "$dir/references" "$dir/playbooks" "$dir/examples" -type f -name '*.md' 2>/dev/null | sort)

report() { # LEVEL FILE MESSAGE FIX
  printf '%s  %s: %s\n      fix: %s\n' "$1" "${2#"$dir"/}" "$3" "$4"
}
fail() { report FAIL "$@"; failed=1; }
warn() { report WARN "$@"; }
finish() { exit "$failed"; }

# The SKILL.md frontmatter, without the --- lines.
frontmatter() {
  [ -f "$skill" ] && awk '{ sub(/\r$/, "") } NR == 1 { if (!/^---$/) exit; next } /^---$/ { exit } { print }' "$skill"
}
skill_name() {
  frontmatter | sed -nE 's/^name:[[:space:]]*["'\'']?([^"'\'']*)["'\'']?[[:space:]]*$/\1/p'
}
# A plain, quoted or folded (>- or |) description, joined into one line.
skill_description() {
  frontmatter | awk '/^description:/ { on = 1; sub(/^description:[ \t]*/, ""); if ($0 !~ /^[>|][-+]?$/) print; next }
    on && /^[ \t]/ { sub(/^[ \t]+/, ""); print; next } { on = 0 }' |
    tr '\n' ' ' | sed -E 's/[[:space:]]+$//; s/^["'\'']//; s/["'\'']$//'
}

# The body of a Markdown file without frontmatter or code fences, as
# LINE<TAB>TEXT.
prose() {
  awk '{ sub(/\r$/, "") }
       NR == 1 && /^---$/ { front = 1; next }
       front { if (/^---$/) front = 0; next }
       /^[ \t]*(```|~~~)/ { fence = !fence; next }
       !fence { print NR "\t" $0 }' "$1"
}

# Each local link target in FILE: Markdown link targets outside inline code,
# and backticked file paths under a skill subdirectory, optionally after the
# skill's own name. Placeholders and bare directories in backticks are skipped.
targets() {
  prose "$1" | cut -f2- | text_targets
}
# The same for the Markdown text on standard input.
text_targets() {
  local text name=${dir##*/}
  text=$(cat)
  {
    sed -E 's/`[^`]*`//g' <<<"$text" | grep -oE '\]\((<[^>]+>|[^)[:space:]]+)' |
      sed -E 's/^\]\(<?//; s/>$//; s/#.*//; s/%20/ /g'
    grep -oE "\`(\./|$name/)?(scripts|references|playbooks|examples|assets)/[^\`[:space:]]*[^/\`[:space:]]\`" <<<"$text" |
      tr -d '`' | sed -E "s#^(\./|$name/)##"
  } | grep -vE '^$|^[a-z]+:|^/|[<>*{}$]'
}

# Resolves a link target from FILE to an existing path, or prints nothing.
resolve() {
  local from="${1%/*}" target="${2#./}"
  if [ -e "$from/$target" ]; then printf '%s\n' "$from/$target"
  elif [ -e "$dir/$target" ]; then printf '%s\n' "$dir/$target"
  fi
}

# Prints PATH<TAB>DEPTH for each file reached from SKILL.md, breadth first. A
# README.md does not pass links on. A link to a directory reaches the .md
# files directly in it. Plain strings, because macOS bash 3.2 has no
# associative arrays.
reached() {
  local seen="$skill	0" queue=("$skill") file target found next linked depth
  depth_of() { awk -F'\t' -v p="$1" '$1 == p { print $2; exit }' <<<"$seen"; }
  while [ "${#queue[@]}" -gt 0 ]; do
    file=${queue[0]}
    queue=("${queue[@]:1}")
    [ -f "$file" ] || continue
    [ "${file##*/}" = README.md ] && continue
    depth=$(($(depth_of "$file") + 1))
    while IFS= read -r target; do
      found=$(resolve "$file" "$target")
      [ -n "$found" ] || continue
      if [ -d "$found" ]; then linked=("${found%/}"/*.md); else linked=("$found"); fi
      for next in "${linked[@]}"; do
        [ -f "$next" ] || continue
        next=$(cd "${next%/*}" && pwd)/${next##*/}
        [ -n "$(depth_of "$next")" ] && continue
        seen="$seen
$next	$depth"
        queue+=("$next")
      done
    done < <(targets "$file")
  done
  printf '%s\n' "$seen"
}
