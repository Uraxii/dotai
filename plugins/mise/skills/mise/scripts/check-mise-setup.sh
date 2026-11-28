#!/bin/bash
# Checks the mise setup of a repository, or of one project in a monorepo.
# Prints a FAIL line and a fix for each problem, then one summary line, and
# exits 1 if there was a problem. It leaves the repository and the mise state
# as they were: it never trusts a config, never installs a tool, and never
# runs a task. It runs `mise tasks` in safe mode (MISE_SAFE=1), so that a
# monorepo project config that is not trusted runs no template exec(). The
# other calls load the config of the checked directory as mise does, so a
# template exec() in a trusted config there does run. It ignores the global and
# system config, except for the trust they give. It hides mise output, which
# can hold [env] values.
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
# `mise trust --show` only reads. It runs before the overrides below, so that
# it sees the trust that the global trusted_config_paths setting gives.
trust=$(mise trust --show 2>/dev/null)

scratch=$(mktemp -d) || exit 2
# Bash runs the EXIT trap on HUP, INT or TERM only when that signal has a trap.
# Every mise command runs in the foreground, so the trap waits for it to end.
trap 'rm -rf "$scratch"' EXIT
trap 'exit 2' HUP INT TERM
# Every mise command, also in safe mode, writes to the mise state. Under a
# trusted monorepo root it writes a file that trusts every project. A copy of
# the state keeps those writes out of the real state.
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

if ! grep -qE ': (trusted|untrusted)$' <<<"$trust"; then
  fail . "no mise config found" "create mise.toml from the skill's templates/mise.toml"
  finish
fi
# `mise run`, `exec` and `install` trust their config with no prompt, so a
# config that is not trusted fails here, even one that mise loads without
# trust. A config above the directory fails only at the monorepo root.
root=
while IFS= read -r line; do
  path=${line%: *}
  path=${path/#\~/"$HOME"}
  (cd "$path" && grep -rqsE '^monorepo_root *= *true' mise.toml .mise.toml mise .mise .config/mise.toml .config/mise) &&
    root=$path
  if [ "${line##*: }" = trusted ]; then
    # Trust from a setting is not in the copy of the state, so the copy gets it.
    quiet mise trust "$path"
    continue
  fi
  case $path/ in "$PWD"/*) ;; *) [ "$path" = "$root" ] || continue ;; esac
  where=${path#"$PWD"/}
  [ "$path" = "$PWD" ] && where=.
  fail "$where" "config is not trusted" "read the config, then run: mise trust $where"
done < <(grep -E ': (trusted|untrusted)$' <<<"$trust")
[ "$failed" = 0 ] || finish

if ! quiet mise config ls; then
  fail mise.toml "mise cannot load the config" \
    "run mise config ls to see why: TOML syntax, a min_version above this mise, or a required [env] value that is not set"
  finish
fi

while IFS= read -r file; do
  fail "$file" "a REPLACE_WITH_ placeholder is left" "replace each REPLACE_WITH_ value"
done < <(grep -rlsI REPLACE_WITH_ mise.toml .mise.toml mise .mise .config/mise.toml .config/mise mise-tasks .mise-tasks)

MISE_SAFE=1 quiet mise tasks validate ||
  fail mise.toml "mise tasks validate fails" \
    "run mise tasks validate to see each error. A task field that calls exec() fails too, because the check runs in safe mode"

missing=0
if ! quiet mise install --dry-run-code; then
  missing=1
  fail mise.toml "a requested tool is not installed" "read the config, then run mise install"
fi

current=$(mise ls --current --no-global --no-header 2>/dev/null)
exact=$(awk '$2 == $NF && $2 !~ /:/ { print $1, $2 }' <<<"$current")
while read -r tool; do
  read -ra requests <<<"$(mise tool "$tool" --requested 2>/dev/null)"
  for requested in "${requests[@]}"; do
    grep -qxF -- "$tool $requested" <<<"$exact" ||
      fail mise.toml "$tool is requested as $requested, not an exact version" \
        "request one exact release, such as: mise use --pin $tool@<version>"
  done
done < <(awk '{ print $1 }' <<<"$current" | sort -u)

[ "$missing" = 0 ] && ! quiet mise install --locked --dry-run-code &&
  fail mise.lock "the lockfile does not list every requested tool" "run mise lock, and commit the lockfile it writes"

# In a monorepo, the names of this project's tasks start with //PROJECT:.
rel=${PWD#"$root"}
project=${root:+//${rel#/}:}
tasks=$(MISE_SAFE=1 mise tasks ls --hidden --no-global --no-header 2>/dev/null |
  p=$project awk 'substr($1, 1, length(ENVIRON["p"])) == ENVIRON["p"]')
while IFS= read -r name; do
  fail "$name" "task has no description" \
    "add description = \"...\" to a TOML task, or #MISE description=\"...\" to a file task"
done < <(awk 'NF == 1 { print $1 }' <<<"$tasks")

awk '{ print $1 }' <<<"$tasks" | grep -qxF -- "${project}ci" ||
  fail mise.toml "no ci task" "add a ci task that depends on lint:* and test:*"
finish
