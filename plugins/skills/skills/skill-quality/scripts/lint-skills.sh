#!/bin/bash
# Checks one skill directory for the skill smells a script can find.
# Prints FAIL and WARN lines, each with a fix, and exits 1 on any FAIL.
#
# Usage: lint-skills.sh SKILL_DIR
# Reference files are the .md files under references/, playbooks/ and
# examples/. A link from a README.md does not route a reference.

[ -d "${1:-}" ] || { echo "usage: lint-skills.sh SKILL_DIR" >&2; exit 2; }
dir=$(cd "$1" && pwd)
skill="$dir/SKILL.md"
fails=0
warns=0

report() { # LEVEL FILE MESSAGE FIX
  printf '%s  %s: %s\n      fix: %s\n' "$1" "${2#"$dir"/}" "$3" "$4"
  if [ "$1" = FAIL ]; then fails=$((fails + 1)); else warns=$((warns + 1)); fi
}

# Prints the body of a Markdown file without code fences, as LINE<TAB>TEXT.
prose() {
  awk 'NR == 1 && /^---$/ { front = 1; next }
       front { if (/^---$/) front = 0; next }
       /^[ \t]*(```|~~~)/ { fence = !fence; next }
       !fence { print NR "\t" $0 }' "$1"
}

# Prints each local link target in FILE: Markdown link targets and
# backticked paths under a skill subdirectory. Placeholders are skipped.
targets() {
  local text
  text=$(prose "$1" | cut -f2-)
  {
    grep -oE '\]\([^)[:space:]]+\)' <<<"$text" | sed -E 's/^\]\(//; s/\)$//; s/#.*//'
    grep -oE '`(\./)?(scripts|references|playbooks|examples|assets)/[^`[:space:]]*`' <<<"$text" | tr -d '`'
  } | grep -vE '^$|^[a-z]+:|^/|[<>*{}$]'
}

# Resolves a link target from FILE to an existing path, or prints nothing.
resolve() {
  local from="${1%/*}" target="${2#./}"
  if [ -e "$from/$target" ]; then printf '%s\n' "$from/$target"
  elif [ -e "$dir/$target" ]; then printf '%s\n' "$dir/$target"
  fi
}

refs=()
while IFS= read -r ref; do refs+=("$ref"); done < <(
  find "$dir/references" "$dir/playbooks" "$dir/examples" -type f -name '*.md' 2>/dev/null | sort)

# --- SKILL.md frontmatter ---
if [ ! -f "$skill" ]; then
  report FAIL "$skill" "SKILL.md is missing" "add SKILL.md with name and description frontmatter"
else
  front=$(awk 'NR == 1 { if (!/^---$/) exit; next } /^---$/ { exit } { print }' "$skill")
  name=$(sed -nE 's/^name:[[:space:]]*["'\'']?([^"'\'']*)["'\'']?[[:space:]]*$/\1/p' <<<"$front")
  # Joins a plain, quoted or folded (>- or |) description into one line.
  description=$(awk '/^description:/ { on = 1; sub(/^description:[ \t]*/, ""); if ($0 !~ /^[>|][-+]?$/) print; next }
    on && /^[ \t]/ { sub(/^[ \t]+/, ""); print; next } { on = 0 }' <<<"$front" |
    tr '\n' ' ' | sed -E 's/[[:space:]]+$//; s/^["'\'']//; s/["'\'']$//')
  if [ -z "$name" ]; then
    report FAIL "$skill" "frontmatter has no name" "add 'name: <directory name>'"
  else
    [ "${#name}" -le 64 ] || report FAIL "$skill" "name is ${#name} characters, over 64" "rename it for discovery"
    [[ "$name" =~ ^[a-z0-9-]+$ ]] || report FAIL "$skill" "name '$name' has characters other than a-z, 0-9 and -" "use lowercase words joined by -"
    [ "$name" = "${dir##*/}" ] || report FAIL "$skill" "name '$name' is not the directory name '${dir##*/}'" "make the name and the directory the same"
  fi
  if [ -z "$description" ]; then
    report FAIL "$skill" "frontmatter has no description" "add a description that says what the skill does and when to use it"
  else
    [ "${#description}" -le 1024 ] || report FAIL "$skill" "description is ${#description} characters, over 1,024" "keep only capability and routing"
    grep -qE '</?[A-Za-z][^>]*>' <<<"$description" &&
      report FAIL "$skill" "description has an XML tag, which can inject instructions" "use plain text"
    grep -qiE '^(use|i |you|this skill)' <<<"$description" &&
      report WARN "$skill" "description is not third person" "start with what the skill does, such as 'Reviews ...'"
    grep -qiE '\b(when|whenever|before|after|use for|use to|triggers?)\b' <<<"$description" ||
      report WARN "$skill" "description does not say when to use the skill" "add 'Use when ...' with discovery keywords"
  fi
  words=$(prose "$skill" | cut -f2- | wc -w | tr -d ' ')
  [ "$words" -le 5000 ] || report FAIL "$skill" "body is $words words, over 5,000" "cut, split, or move detail to references"
fi

# --- All Markdown: backslash paths, broken links, decaying facts ---
for file in "$skill" "${refs[@]}"; do
  [ -f "$file" ] || continue
  while IFS=$'\t' read -r line text; do
    [[ "$text" =~ (scripts|references|playbooks|examples|assets)\\ ]] &&
      report FAIL "$file" "line $line has a backslash path" "use / in skill paths"
    grep -qiE '\b(as of|currently|new in)\b|\b20[0-9]{2}\b' <<<"$text" &&
      report WARN "$file" "line $line may hold a fact that decays: ${text:0:80}" "query the source at use, name an update rule, or cut the claim"
  done < <(prose "$file")
  while IFS= read -r target; do
    [ -n "$(resolve "$file" "$target")" ] ||
      report FAIL "$file" "link to $target does not resolve" "fix the path, or add the file"
  done < <(targets "$file")
done

# --- References: orphans, depth, contents list ---
# Breadth-first from SKILL.md. A README.md does not pass links on. A link to a
# directory reaches the .md files directly in it.
declare -A depth=()
[ -f "$skill" ] && depth["$skill"]=0
queue=("$skill")
while [ "${#queue[@]}" -gt 0 ]; do
  file=${queue[0]}
  queue=("${queue[@]:1}")
  [ -f "$file" ] || continue
  [ "${file##*/}" = README.md ] && continue
  while IFS= read -r target; do
    found=$(resolve "$file" "$target") || continue
    [ -n "$found" ] || continue
    if [ -d "$found" ]; then
      linked=("${found%/}"/*.md)
    else
      linked=("$found")
    fi
    for next in "${linked[@]}"; do
      [ -f "$next" ] || continue
      next=$(cd "${next%/*}" && pwd)/${next##*/}
      next=${next#"$(cd "$dir" && pwd)"/}
      next="$dir/$next"
      [ -n "${depth[$next]+set}" ] && continue
      depth["$next"]=$((depth["$file"] + 1))
      queue+=("$next")
    done
  done < <(targets "$file")
done

for ref in "${refs[@]}"; do
  if [ -z "${depth[$ref]+set}" ]; then
    report FAIL "$ref" "no link from SKILL.md or a linked reference reaches this file" \
      "link it from SKILL.md with when to read it, or delete it"
  elif [ "${depth[$ref]}" -gt 1 ]; then
    report WARN "$ref" "this file is ${depth[$ref]} links from SKILL.md, so agents may read it only in part" \
      "link it directly from SKILL.md"
  fi
  lines=$(wc -l <"$ref" | tr -d ' ')
  if [ "$lines" -gt 100 ] &&
    ! head -n 40 "$ref" | grep -qiE '^#+ .*contents|\]\(#'; then
    report WARN "$ref" "file has $lines lines and no table of contents near the top" \
      "add a contents list after the title"
  fi
done

printf 'lint-skills.sh: %s: %d failed, %d warnings\n' "$dir" "$fails" "$warns"
[ "$fails" -eq 0 ]
