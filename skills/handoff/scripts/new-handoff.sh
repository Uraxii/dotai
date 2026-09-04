#!/usr/bin/env bash
# Create a handoff file: pick the outdir, next chain number, and skeleton.
# Usage: new-handoff.sh <project> <topic> [outdir]
set -euo pipefail

if [ "$#" -lt 2 ] || [ "$#" -gt 3 ]; then
	printf 'usage: new-handoff.sh <project> <topic> [outdir]\n' >&2
	exit 1
fi

project="$1"
topic="$2"
repo_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
outdir="${3:-${repo_root:-$PWD}/.handoffs}"
mkdir -p "$outdir"

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

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
template="$script_dir/../references/document-structure.md"
sed -n '/^# Handoff:/,$p' "$template" > "$dest"

if [ -n "$repo_root" ]; then
	gitignore="$repo_root/.gitignore"
	if [ -s "$gitignore" ] && [ -n "$(tail -c1 "$gitignore")" ]; then
		printf '\n' >> "$gitignore"
	fi
	grep -qxF '.handoffs/' "$gitignore" 2>/dev/null || printf '.handoffs/\n' >> "$gitignore"
fi

realpath "$dest"
