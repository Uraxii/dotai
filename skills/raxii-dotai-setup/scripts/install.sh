#!/usr/bin/env bash
# Copy this repo's skills, agents, and harness config into the harness config
# dirs under $HOME. Copies, never symlinks. Every written file is recorded in a
# per-target-root manifest so --prune can delete what a previous run wrote and
# this run did not, and nothing else.
set -euo pipefail

MANIFEST_NAME=.dotai-manifest
DRY=0
PRUNE=0
MODE=
REPO=

die() { printf 'install.sh: %s\n' "$*" >&2; exit 1; }
say() { printf '%s\n' "$*"; }
# Per-file chatter is only useful when nothing is actually happening.
vsay() { [ "$DRY" = 1 ] && printf '%s\n' "$*"; return 0; }

usage() {
  cat <<'EOF'
usage: install.sh --harness <claude|codex|copilot|opencode|hermes|all>
                  [--dry-run] [--prune] [--repo <path>]

  --harness   which harness to install for; "all" does every one
  --dry-run   print every action, write nothing
  --prune     delete files the previous manifest lists and this run did not write
  --repo      source repo root; defaults to this script's own repo
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --harness) MODE=${2:-}; shift $(( $# > 1 ? 2 : 1 )) ;;
    --repo)    REPO=${2:-}; shift $(( $# > 1 ? 2 : 1 )) ;;
    --dry-run) DRY=1; shift ;;
    --prune)   PRUNE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; die "unknown argument: $1" ;;
  esac
done

[ -n "$MODE" ] || { usage >&2; die "--harness is required"; }

if [ -z "$REPO" ]; then
  REPO=$(cd -- "$(dirname -- "$0")/../../.." && pwd)
fi
[ -d "$REPO" ] || die "repo not found: $REPO"
[ -d "$REPO/skills" ] || die "not a dotai repo, no skills dir: $REPO"

case "$MODE" in
  all) set -- claude codex copilot opencode hermes ;;
  claude|codex|copilot|opencode|hermes) set -- "$MODE" ;;
  *) die "unknown harness: $MODE" ;;
esac

# One job per line: <repo subdir>|<target root>|<subdir under target root>.
# Jobs sharing a target root share its manifest. Skills come before the
jobs_for() {
  case "$1" in
    claude)   printf '%s\n' "skills|$HOME/.claude|skills" \
                            "agents|$HOME/.claude|agents" ;;
    codex)    printf '%s\n' "skills|$HOME/.agents|skills" ;;
    copilot)  printf '%s\n' "skills|$HOME/.copilot|skills" ;;
    opencode) printf '%s\n' "skills|$HOME/.config/opencode|skills" ;;
    hermes)   printf '%s\n' "skills|$HOME/.hermes|skills" ;;
  esac
}

SEEN=
# Make $1 a real directory, replacing any symlink or file standing where a
# directory belongs. Leftover stow deploys leave exactly that.
ensure_dir() {
  case "$SEEN" in *"[$1]"*) return 0 ;; esac
  if [ -d "$1" ] && [ ! -L "$1" ]; then SEEN="${SEEN}[$1]"; return 0; fi
  ensure_dir "$(dirname -- "$1")"
  if [ -L "$1" ] || [ -e "$1" ]; then
    say "  unlink-dir $1"
    [ "$DRY" = 1 ] || rm -f "$1"
  fi
  [ "$DRY" = 1 ] || mkdir -p "$1"
  SEEN="${SEEN}[$1]"
}

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

for harness in "$@"; do
  jobs_for "$harness" > "$TMP/jobs"
  hw=0; hs=0; hp=0

  cut -d'|' -f2 < "$TMP/jobs" | awk '!seen[$0]++' > "$TMP/roots"
  while IFS= read -r root; do
    : > "$TMP/pairs"
    while IFS='|' read -r jsrc jroot jsub; do
      [ "$jroot" = "$root" ] || continue
      srcdir="$REPO/$jsrc"
      [ -d "$srcdir" ] || die "missing repo dir: $srcdir"
      find "$srcdir" \
        \( -name __pycache__ -o -name .pytest_cache -o -name .ruff_cache \
           -o -name raxii-dotai-setup \
           -o -name .git \) -prune \
        -o -type f ! -name '*.pyc' -print |
      while IFS= read -r f; do
        rel=${f#"$srcdir"/}
        if [ -n "$jsub" ]; then rel="$jsub/$rel"; fi
        printf '%s|%s\n' "$f" "$rel"
      done >> "$TMP/pairs"
    done < "$TMP/jobs"

    : > "$TMP/new"
    while IFS='|' read -r srcfile rel; do
      printf '%s\n' "$rel" >> "$TMP/new"
      dst="$root/$rel"
      if [ -f "$dst" ] && [ ! -L "$dst" ] && cmp -s "$srcfile" "$dst"; then
        hs=$(( hs + 1 ))
        continue
      fi
      ensure_dir "$(dirname -- "$dst")"
      if [ -L "$dst" ]; then say "  unlink $dst"; fi
      vsay "  write  $dst"
      if [ "$DRY" != 1 ]; then
        rm -f "$dst"
        cp -p "$srcfile" "$dst"
      fi
      hw=$(( hw + 1 ))
    done < "$TMP/pairs"

    manifest="$root/$MANIFEST_NAME"
    if [ "$PRUNE" = 1 ] && [ -f "$manifest" ]; then
      sort -u "$TMP/new" > "$TMP/new.sorted"
      sort -u "$manifest" > "$TMP/old.sorted"
      comm -23 "$TMP/old.sorted" "$TMP/new.sorted" > "$TMP/gone"
      while IFS= read -r rel; do
        [ -n "$rel" ] || continue
        old="$root/$rel"
        if [ -e "$old" ] || [ -L "$old" ]; then
          say "  prune  $old"
          if [ "$DRY" != 1 ]; then
            rm -f "$old"
            rmdir -p "$(dirname -- "$old")" 2>/dev/null || true
          fi
          hp=$(( hp + 1 ))
        fi
      done < "$TMP/gone"
    fi

    if [ "$DRY" != 1 ]; then
      ensure_dir "$root"
      sort -u "$TMP/new" > "$manifest"
    else
      vsay "  manifest $manifest"
    fi
  done < "$TMP/roots"

  printf '%-9s written=%-5s pruned=%-5s skipped=%s\n' \
    "$harness" "$hw" "$hp" "$hs"
done
