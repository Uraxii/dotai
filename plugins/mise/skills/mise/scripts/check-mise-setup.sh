#!/bin/bash
# Checks the mise setup of a repository, or of one project in a monorepo.
# Prints a FAIL line and a fix for each problem, then one summary line, and
# exits 1 if there was a problem. Exits 2 if it cannot run: bad usage, no mise,
# git or tar on PATH, or a directory that is not in a git work tree.
#
# It judges a clean copy of the repository, so that the result is the same on
# each machine. The copy holds the files that git does not ignore: tracked
# files as they are on disk, and new files that no .gitignore rule matches.
# The check runs mise in the copy with no MISE_* variable from the caller,
# except the ones that say where installed tools are, and with no global or
# system config. A file that git ignores, such as mise.local.toml, is not in
# the copy. A local config that git does not ignore fails the check and is
# not in the copy.
#
# It leaves the repository and the mise state as they were: it never trusts a
# config of the repository, never installs a tool, and never runs a task. It
# reads the trust that this machine gives each config of the repository, and
# trusts in the copy, in a mise state of its own, only a config that is
# trusted there. In a monorepo it runs `mise tasks` in safe mode
# (MISE_SAFE=1), so that a project config that is not trusted runs no template
# exec(). The other calls load the config of the checked directory as mise
# does, so a template exec() in a trusted config there does run, in the copy.
# It ignores each config above the checked directory, or above the monorepo
# root. It still names a REPLACE_WITH_ placeholder in a local config of the
# repository. It hides mise output, which can hold [env] values.
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
for tool in mise git tar; do
  command -v "$tool" >/dev/null || { echo "check-mise-setup.sh: $tool is not on PATH" >&2; exit 2; }
done
# mise prints real paths, so the directory must not be behind a symlink.
cd -P "$dir" || exit 2
here=$PWD
worktree=$(git rev-parse --show-toplevel) && subdir=$(git rev-parse --show-prefix) &&
  gitdir=$(git rev-parse --absolute-git-dir) ||
  { echo "check-mise-setup.sh: $here is not in a git work tree" >&2; exit 2; }
failed=0

keep_mise_variables() { # NAME...: unsets each other MISE_* variable
  local name
  for name in $(compgen -e); do
    [[ $name == MISE_* || $name == __MISE_* ]] && [[ " $* " != *" $name "* ]] && unset "$name"
  done
}
# Where the installed tools and the download cache are, and no network if the
# caller has none. The check must find the tools that are installed here.
installs="MISE_DATA_DIR MISE_CACHE_DIR MISE_SYSTEM_DATA_DIR MISE_SHARED_INSTALL_DIRS MISE_OFFLINE"
# The trust that this machine gives comes from the mise state, from the global
# and system config, and from these two variables.
keep_mise_variables $installs MISE_STATE_DIR MISE_CONFIG_DIR MISE_GLOBAL_CONFIG_FILE \
  MISE_SYSTEM_CONFIG_DIR MISE_SYSTEM_CONFIG_FILE MISE_TRUSTED_CONFIG_PATHS MISE_PARANOID
# `mise trust --show` only reads. It is the one mise call in the repository.
real_trust=$(mise trust --show 2>/dev/null </dev/null)
in_real_trust() { # DIR STATUS: true if that list gives DIR that status. mise prints ~ for $HOME.
  local short=$1
  case $1 in "$HOME" | "$HOME"/*) short="~${1#"$HOME"}" ;; esac
  grep -qxF -e "$1: $2" -e "$short: $2" <<<"$real_trust"
}
keep_mise_variables $installs

scratch=$(mktemp -d) || exit 2
# Bash runs the EXIT trap on HUP, INT or TERM only when that signal has a trap.
# Every mise command runs in the foreground, so the trap waits for it to end.
trap 'rm -rf "$scratch"' EXIT
trap 'exit 2' HUP INT TERM
scratch=$(cd -P "$scratch" && pwd) || exit 2
copy=$scratch/repo
mkdir -p "$scratch/state" "$scratch/config" "$copy/$subdir" && : >"$scratch/local" || exit 2
# A config that mise reads for one machine. The playbook keeps it out of git.
local_config='(^|/)\.?mise[^/]*\.local\.toml$|(^|/)\.?mise/.*\.local\.toml$'
# tar copies a symbolic link as a link, and git lists no path below one.
(cd "$worktree" && git ls-files -z --cached --others --exclude-standard |
  while IFS= read -r -d '' file; do
    # A deleted file and a submodule are in the list, and are not files.
    [ -f "$file" ] || [ -L "$file" ] || continue
    case $worktree/$file in "$scratch"/*) continue ;; esac
    if [[ $file =~ $local_config ]]; then
      [[ $file == "$subdir"* ]] && printf '%s\n' "${file#"$subdir"}" >>"$scratch/local"
      continue
    fi
    printf '%s\0' "$file"
  done | tar -cf - --null -T -) | tar -xf - -C "$copy" || exit 2
# A template that calls git reads the repository, as it does outside the copy.
printf 'gitdir: %s\n' "$gitdir" >"$copy/.git"
cd "$copy/$subdir" || exit 2
# mise loads no config from a ceiling path or from above it.
export MISE_STATE_DIR="$scratch/state" MISE_CONFIG_DIR="$scratch/config" MISE_SYSTEM_CONFIG_DIR="$scratch/config" \
  MISE_GLOBAL_CONFIG_FILE="$scratch/config/config.toml" MISE_SYSTEM_CONFIG_FILE="$scratch/config/config.toml" \
  MISE_CEILING_PATHS="$scratch"

fail() { # WHERE MESSAGE FIX
  printf 'FAIL  %s: %s\n      fix: %s\n' "$1" "$2" "$3"
  failed=$((failed + 1))
}
quiet() { "$@" >/dev/null 2>&1 </dev/null; }
finish() {
  printf 'check-mise-setup.sh: %s: %d failed\n' "$here" "$failed"
  exit $((failed > 0))
}

# `mise run`, `exec` and `install` trust their config with no prompt, so a
# config that is not trusted fails here, even one that mise loads without
# trust. A config above the directory fails only at the monorepo root. The
# list comes from the copy, so a file that git ignores adds no config to it.
# A process substitution is not a foreground command, so mise does not run in one.
copy_trust=$(mise trust --show 2>/dev/null </dev/null)
root=
found=0
while IFS= read -r line; do
  path=${line%: *}
  path=${path/#\~/"$HOME"}
  real=$worktree${path#"$copy"}
  [ "$path" = "$PWD" ] && found=1
  (cd "$path" && grep -rqsE '^monorepo_root *= *true' mise.toml .mise.toml mise .mise .config/mise.toml .config/mise) &&
    root=$path
  if in_real_trust "$real" trusted; then
    quiet mise trust "$path"
    continue
  fi
  case $path in "$PWD") where=. ;; "$PWD"/*) where=${path#"$PWD"/} ;; "$root") where=$real ;; *) continue ;; esac
  # A setting of this machine, such as override_config_filenames in a
  # .miserc.local.toml, can make mise read no config in this directory.
  in_real_trust "$real" untrusted || {
    echo "check-mise-setup.sh: mise reads no config in $real on this machine, so its trust is not known" >&2
    exit 2
  }
  fail "$where" "config is not trusted" "read the config, then run: mise trust $where"
done < <(grep ': untrusted$' <<<"$copy_trust")
# A config above the directory does not make it a mise repository.
[ "$found" = 1 ] || fail . "no mise config found" "create mise.toml from the skill's templates/mise.toml"
[ "$failed" = 0 ] || finish
top=${root:-$PWD}
export MISE_CEILING_PATHS="${top%/*}/"
while IFS= read -r file; do
  fail "$file" "git does not ignore this local config" \
    "add it to .gitignore, and if git tracks it, run: git rm --cached $file"
done <"$scratch/local"
# Under a trusted monorepo root, mise trusts each project config, so `mise
# tasks` runs in safe mode there. Safe mode drops [env].
safe=${root:+1}

if ! quiet mise config ls; then
  fail mise.toml "mise cannot load the config" \
    "run mise config ls to see why: TOML syntax, a min_version above this mise, or a required [env] value that is not set"
  finish
fi

while IFS= read -r file; do
  fail "$file" "a REPLACE_WITH_ placeholder is left" "replace each REPLACE_WITH_ value"
done < <(cd "$here" && grep -rlsI REPLACE_WITH_ mise.toml .mise.toml mise.*.toml .mise.*.toml mise .mise \
  .config/mise.toml .config/mise.*.toml .config/mise mise-tasks .mise-tasks)

MISE_SAFE=$safe quiet mise tasks validate ||
  fail mise.toml "mise tasks validate fails" \
    "run mise tasks validate to see each error. In a monorepo, a task field that calls exec() or reads [env] fails too, because the check runs in safe mode there"

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

# MISE_LOCKFILE=1: with lockfile = false, mise passes --locked with no lockfile.
[ "$missing" = 0 ] && ! MISE_LOCKFILE=1 quiet mise install --locked --dry-run-code &&
  fail mise.lock "the lockfile does not list every requested tool" "run mise lock, and commit the lockfile it writes"

# In a monorepo, the names of this project's tasks start with //PROJECT:.
rel=${PWD#"$root"}
project=${root:+//${rel#/}:}
tasks=$(MISE_SAFE=$safe mise tasks ls --hidden --no-global --no-header 2>/dev/null |
  p=$project awk 'substr($1, 1, length(ENVIRON["p"])) == ENVIRON["p"]')
while IFS= read -r name; do
  fail "$name" "task has no description" \
    "add description = \"...\" to a TOML task, or #MISE description=\"...\" to a file task"
done < <(awk 'NF == 1 { print $1 }' <<<"$tasks")

awk '{ print $1 }' <<<"$tasks" | grep -qxF -- "${project}ci" ||
  fail mise.toml "no ci task" "add a ci task that depends on lint:* and test:*"
finish
