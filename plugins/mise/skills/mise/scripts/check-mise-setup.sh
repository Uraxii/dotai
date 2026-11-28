#!/bin/bash
# Checks the mise setup of a repository, or of one project in a monorepo.
# Prints a FAIL line and a fix for each problem, then one summary line, and
# exits 1 if there was a problem. It leaves the repository and the mise state
# as they were: it never trusts a config, never installs a tool, and never
# runs a task. It ignores the global and system config. It hides mise output,
# which can hold [env] values.
#
# Usage: check-mise-setup.sh [-C DIR]

usage() { echo "usage: check-mise-setup.sh [-C DIR]" >&2; exit 2; }
dir=.
while [ $# -gt 0 ]; do
  case $1 in
    -C) [ -n "${2:-}" ] || usage; dir=$2; shift 2 ;;
    *) usage ;;
  esac
done
command -v mise >/dev/null || { echo "check-mise-setup.sh: mise is not on PATH" >&2; exit 2; }
cd "$dir" || exit 2
failed=0

scratch=$(mktemp -d) || exit 2
trap 'rm -rf "$scratch"' EXIT
# Under a trusted monorepo root, mise writes a state file that trusts every
# project. A copy of the state keeps that write out of the real state.
state=${MISE_STATE_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/mise}
mkdir "$scratch/state" "$scratch/config"
[ -d "$state" ] && { cp -RP "$state/." "$scratch/state" || exit 2; }
export MISE_STATE_DIR="$scratch/state" MISE_CONFIG_DIR="$scratch/config" \
  MISE_GLOBAL_CONFIG_FILE="$scratch/config/config.toml" MISE_SYSTEM_CONFIG_FILE="$scratch/config/config.toml"

fail() { # WHERE MESSAGE FIX
  printf 'FAIL  %s: %s\n      fix: %s\n' "$1" "$2" "$3"
  failed=$((failed + 1))
}
quiet() { "$@" >/dev/null 2>&1; }
finish() {
  printf 'check-mise-setup.sh: %s: %d failed\n' "$PWD" "$failed"
  exit $((failed > 0))
}

# `mise trust --show` only reads. Every later command needs a trusted config,
# and `mise run`, `exec` and `install` would trust one with no prompt.
trust=$(mise trust --show 2>/dev/null)
if ! grep -qE ': (trusted|untrusted)$' <<<"$trust"; then
  fail . "no mise config found" "create mise.toml from the skill's templates/mise.toml"
  finish
fi
while IFS= read -r path; do
  where=${path#"$PWD"/}
  [ "$path" = "$PWD" ] && where=.
  fail "$where" "config is not trusted" "read the config, then run: mise trust $where"
done < <(sed -nE 's/: untrusted$//p' <<<"$trust")
[ "$failed" = 0 ] || finish

if ! quiet mise config ls; then
  fail mise.toml "mise cannot load the config" \
    "run mise config ls to see why: TOML syntax, a min_version above this mise, or a required [env] value that is not set"
  finish
fi

while IFS= read -r file; do
  fail "$file" "a REPLACE_WITH_ placeholder is left" "replace each REPLACE_WITH_ value"
done < <(grep -rlsI REPLACE_WITH_ mise.toml .mise.toml mise .mise .config/mise.toml .config/mise mise-tasks .mise-tasks)

quiet mise tasks validate ||
  fail mise.toml "mise tasks validate fails" "run mise tasks validate to see each error"

missing=0
if ! quiet mise install --dry-run-code; then
  missing=1
  fail mise.toml "a requested tool is not installed" "read the config, then run mise install"
fi

current=$(mise ls --current --no-global --no-header 2>/dev/null)
exact=$(awk '$2 == $NF && $2 !~ /:/ { print $1, $2 }' <<<"$current")
while read -r tool; do
  read -ra requests < <(mise tool "$tool" --requested 2>/dev/null)
  for requested in "${requests[@]}"; do
    grep -qxF -- "$tool $requested" <<<"$exact" ||
      fail mise.toml "$tool is requested as $requested, not an exact version" \
        "request one exact release, such as: mise use --pin $tool@<version>"
  done
done < <(awk '{ print $1 }' <<<"$current" | sort -u)

[ "$missing" = 0 ] && ! quiet mise install --locked --dry-run-code &&
  fail mise.lock "the lockfile does not list every requested tool" "run mise lock, and commit the lockfile it writes"

while IFS= read -r name; do
  fail "$name" "task has no description" \
    "add description = \"...\" to a TOML task, or #MISE description=\"...\" to a file task"
done < <(mise tasks ls --all --hidden --no-global --no-header 2>/dev/null | awk 'NF == 1 { print $1 }')

mise tasks ls --all --hidden --no-global --name-only 2>/dev/null | grep -qxE '(//:)?ci' ||
  fail mise.toml "no ci task" "add a ci task that depends on lint:* and test:*"
finish
