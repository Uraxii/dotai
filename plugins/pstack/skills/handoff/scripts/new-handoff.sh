#!/usr/bin/env bash
# Create a handoff file: pick the outdir, next chain number, and contents.
# Usage: new-handoff.sh --stdin|--skeleton <project> <topic> [outdir]
set -euo pipefail

usage() {
	printf 'usage: new-handoff.sh --stdin|--skeleton <project> <topic> [outdir]\n' >&2
	printf '  --stdin     read the finished handoff body from stdin\n' >&2
	printf '  --skeleton  write the blank template, read nothing\n' >&2
	exit 1
}

mode=
pos=()
for arg in "$@"; do
	case "$arg" in
	--stdin | --skeleton) [ -z "$mode" ] || usage; mode="$arg" ;;
	-*) usage ;;
	*) pos+=("$arg") ;;
	esac
done
[ -n "$mode" ] || usage
[ "${#pos[@]}" -ge 2 ] && [ "${#pos[@]}" -le 3 ] || usage

# Read the body before creating anything, so a killed run leaves no orphan
# file to inflate every later chain number.
if [ "$mode" = --stdin ]; then
	body="$(cat)"
	body="${body#$'\xef\xbb\xbf'}"
	body="${body#"${body%%[![:space:]]*}"}"
	case "$body" in
	'# Handoff:'*) ;;
	*)
		printf 'body must start with "# Handoff:", nothing written\n' >&2
		exit 1
		;;
	esac
else
	script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
	body="$(sed -n '/^# Handoff:/,$p' \
		"$script_dir/../references/document-structure.md")"
fi

project="${pos[0]}"
topic="${pos[1]}"
repo_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
outdir="${pos[2]:-${repo_root:-$PWD}/.handoffs}"
mkdir -p -- "$outdir"
outdir="$(cd -- "$outdir" && pwd -P)"

prefix="handoff_${project}_${topic}_"
shopt -s nullglob
chain=0
for f in "$outdir/$prefix"*.md; do
	rest="${f##*/"$prefix"}"
	n="${rest%%_*}"
	case "$n" in ''|*[!0-9]*) continue ;; esac
	[ "$n" -gt "$chain" ] && chain="$n"
done
chain=$((chain + 1))

dest="$outdir/${prefix}${chain}_$(date +%s).md"
[ -e "$dest" ] && { printf 'refuse to overwrite %s\n' "$dest" >&2; exit 1; }

# Stage beside $dest so the rename is atomic and a partial write never lands
# under a handoff name. $(...) stripped every trailing newline, so printf
# puts exactly one back.
tmp="$(mktemp "$outdir/.handoff.XXXXXX")"
trap 'rm -f -- "$tmp"' EXIT
printf '%s\n' "$body" > "$tmp"
mv -- "$tmp" "$dest"

if [ -n "$repo_root" ] && [ "${outdir#"$repo_root"/}" != "$outdir" ]; then
	gitignore="$repo_root/.gitignore"
	if [ -s "$gitignore" ] && [ -n "$(tail -c1 "$gitignore")" ]; then
		printf '\n' >> "$gitignore"
	fi
	grep -qxF '.handoffs/' "$gitignore" 2>/dev/null ||
		printf '.handoffs/\n' >> "$gitignore"
fi

printf '%s\n' "$dest"
