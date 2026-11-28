#!/bin/bash
# Checks the mise setup of a repository. Prints a FAIL line and a fix for
# each problem, and exits 1 if there was one. It never trusts a config and
# never installs a tool. It hides mise output, which can hold [env] values.
#
# Usage: check-mise-setup.sh [-C DIR] [--run TASK]
# --run TASK runs one task from `mise tasks ls` after every check passes.

usage() { echo "usage: check-mise-setup.sh [-C DIR] [--run TASK]" >&2; exit 2; }
dir=.
task=
while [ $# -gt 0 ]; do
  case $1 in
    -C) [ -n "${2:-}" ] || usage; dir=$2; shift 2 ;;
    --run) [ -n "${2:-}" ] || usage; task=$2; shift 2 ;;
    *) usage ;;
  esac
done
cd "$dir" || exit 2
failed=0

fail() { # WHERE MESSAGE FIX
  printf 'FAIL  %s: %s\n      fix: %s\n' "$1" "$2" "$3"
  failed=1
}
quiet() { "$@" >/dev/null 2>&1; }

# `mise trust --show` only reads. Every later command needs a trusted config,
# and `mise run`, `exec` and `install` would trust one with no prompt.
trust=$(mise trust --show 2>/dev/null)
if ! grep -qE ': (trusted|untrusted)$' <<<"$trust"; then
  fail . "no mise config found" "create mise.toml from the skill's templates/mise.toml"
  exit 1
fi
while IFS= read -r path; do
  where=${path#"$PWD"/}
  [ "$path" = "$PWD" ] && where=.
  fail "$where" "config is not trusted" "read the config, then run: mise trust $where"
done < <(sed -nE 's/: untrusted$//p' <<<"$trust")
[ "$failed" = 0 ] || exit 1

if ! quiet mise config ls; then
  fail mise.toml "config does not parse" "run mise config ls to see the error"
  exit 1
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

while read -r tool version requested; do
  fail mise.toml "$tool is requested as $requested, not an exact version" "run: mise use --pin $tool@$version"
done < <(mise ls --current --no-global --no-header 2>/dev/null | awk '$2 != $NF { print $1, $2, $NF }')

if [ ! -f mise.lock ]; then
  fail mise.lock "mise.lock does not exist" "set lockfile = true under [settings], run mise install, and commit mise.lock"
elif [ "$missing" = 0 ] && ! quiet mise install --locked --dry-run-code; then
  fail mise.lock "mise.lock does not list every requested tool" "run mise install, and commit mise.lock"
fi

while IFS= read -r name; do
  fail "$name" "task has no description" "add description = \"...\" to the task"
done < <(mise tasks ls --all --hidden --no-header 2>/dev/null | awk 'NF == 1 { print $1 }')

names=$(mise tasks ls --all --hidden --name-only 2>/dev/null)
grep -qxE '(//:)?ci' <<<"$names" ||
  fail mise.toml "no ci task" "add a ci task that depends on lint:* and test:*"

if [ -n "$task" ]; then
  if ! grep -qxF -- "$task" <<<"$names"; then
    fail "$task" "task is not in mise tasks ls" "pass a name that mise tasks ls prints"
  elif [ "$failed" = 1 ]; then
    fail "$task" "task was not run, because a check failed" "fix each FAIL above"
  elif ! mise run "$task"; then
    fail "$task" "mise run $task fails" "read the task output above"
  fi
fi
exit "$failed"
