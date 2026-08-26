#!/usr/bin/env bash
# setup.sh — deploy every dotai package via stow, one per AI harness.
#
# Extra args are forwarded to stow, so you can use its own flags:
#   ./setup.sh          # safe default: stops on any conflict
#   ./setup.sh -R       # restow (unstow + stow) to fix stale links
#   ./setup.sh -n       # simulate, touch nothing
set -eu
cd "$(dirname "$(readlink -f "$0")")"

# deploy PACKAGE into target dir $1, forwarding any stow flags/args.
deploy() {
  t=$1
  shift
  mkdir -p "$t"
  stow -d "$PWD" -t "$t" --no-folding "$@"
}

# SOUL.md files are static identity files tracked by dotai now. If a
# pre-existing live copy matches the tracked copy, remove it so stow can
# replace it with a symlink. If it differs, leave it in place so stow reports
# the conflict instead of overwriting local persona edits.
while IFS= read -r src; do
  rel="${src#"$PWD/.hermes/"}"
  dst="$HOME/.hermes/$rel"
  if [ -f "$dst" ] && cmp -s "$src" "$dst"; then
    rm "$dst"
  fi
done <<EOF2
$(find "$PWD/.hermes" -path '*/SOUL.md' -type f | sort)
EOF2

deploy "$HOME/.claude" "$@" .claude
deploy "$HOME/.hermes" "$@" .hermes
deploy "$HOME/.config/opencode" "$@" opencode
./copilot/install.sh

# Adding another AI harness later (e.g. pi — see deps.toml groups.ai) is one
# more `deploy "$HOME/.pi" "$@" .pi` line above, plus a package dir here.
