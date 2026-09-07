#!/usr/bin/env bash
# Create a handoff file: pick the outdir, next chain number, and contents.
# Usage: new-handoff.sh [--stdin] <project> <topic> [outdir]
# --stdin reads the finished handoff body from stdin. Without it, the file is
# seeded with the skeleton from references/document-structure.md.
set -euo pipefail

usage() {
	printf 'usage: new-handoff.sh [--stdin] <project> <topic> [outdir]\n' >&2
	exit 1
}

from_stdin=0
pos=()
for arg in "$@"; do
	case "$arg" in
	--stdin) from_stdin=1 ;;
	-*) usage ;;
	*) pos+=("$arg") ;;
	esac
done
if [ "${#pos[@]}" -lt 2 ] || [ "${#pos[@]}" -gt 3 ]; then
	usage
fi

# Read the body before creating anything, so a killed run leaves no orphan
# file to inflate every later chain number.
if [ "$from_stdin" -eq 1 ]; then
	body="$(cat)"
	case "$body" in
	'')
		printf 'empty handoff body on stdin, nothing written\n' >&2
		exit 1
		;;
	'# Handoff:'*) ;;
	*)
		printf 'body does not start with "# Handoff:", nothing written\n' >&2
		exit 1
		;;
	esac
elif IFS= read -r -t 0.2 -N 1 _byte 2>/dev/null; then
	printf 'body on stdin but --stdin missing, nothing written\n' >&2
	exit 1
else
	script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
	body="$(sed -n '/^# Handoff:/,$p' \
		"$script_dir/../references/document-structure.md")"
fi

project="${pos[0]}"
topic="${pos[1]}"
repo_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
outdir="${pos[2]:-${repo_root:-$PWD}/.handoffs}"
mkdir -p -- "$outdir"

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

ts="$(date +%s)"
dest="$outdir/${prefix}${chain}_${ts}.md"
[ -e "$dest" ] && { printf 'refuse to overwrite %s\n' "$dest" >&2; exit 1; }

# $(...) stripped every trailing newline, so this restores exactly one.
printf '%s\n' "$body" > "$dest" || {
	printf 'could not write %s\n' "$dest" >&2
	exit 1
}

if [ -n "$repo_root" ]; then
	gitignore="$repo_root/.gitignore"
	if [ -s "$gitignore" ] && [ -n "$(tail -c1 "$gitignore")" ]; then
		printf '\n' >> "$gitignore"
	fi
	grep -qxF '.handoffs/' "$gitignore" 2>/dev/null || printf '.handoffs/\n' >> "$gitignore"
fi

realpath "$dest"
