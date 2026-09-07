#!/usr/bin/env bash
# Create a handoff file: pick the outdir, next chain number, and contents.
# Usage: new-handoff.sh [--stdin] <project> <topic> [outdir]
# --stdin reads the finished handoff body from stdin. Without it, the file is
# seeded with the skeleton from references/document-structure.md.
set -euo pipefail

from_stdin=0
if [ "${1:-}" = "--stdin" ]; then
	from_stdin=1
	shift
fi

if [ "$#" -lt 2 ] || [ "$#" -gt 3 ]; then
	printf 'usage: new-handoff.sh [--stdin] <project> <topic> [outdir]\n' >&2
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

if [ "$from_stdin" -eq 1 ]; then
	if ! cat > "$dest" || [ ! -s "$dest" ]; then
		rm -f "$dest"
		printf 'no handoff body on stdin, nothing written\n' >&2
		exit 1
	fi
else
	script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
	sed -n '/^# Handoff:/,$p' \
		"$script_dir/../references/document-structure.md" > "$dest"
fi

if [ -n "$repo_root" ]; then
	gitignore="$repo_root/.gitignore"
	if [ -s "$gitignore" ] && [ -n "$(tail -c1 "$gitignore")" ]; then
		printf '\n' >> "$gitignore"
	fi
	grep -qxF '.handoffs/' "$gitignore" 2>/dev/null || printf '.handoffs/\n' >> "$gitignore"
fi

realpath "$dest"
