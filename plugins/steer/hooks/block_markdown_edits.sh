#!/usr/bin/env bash
# block_markdown_edits: PreToolUse hook that denies Write, Edit and MultiEdit
# on a markdown file (.md, .markdown, .mdx, any case) unless the file is in
# the project's .ai/ scratch folder, is a plan file an agent harness writes,
# or the user asked.
#
# Wired in the plugin's hooks/claude-hooks.json. It needs only bash, awk and
# git, so Git Bash runs it on Windows. block_markdown_edits.awk reads the JSON.
#
# The project's .ai/ folder is <root>/.ai, where <root> is the git top level
# of the target's nearest existing directory, so a worktree's own .ai/ counts.
# Outside a git repo, <root> is $CLAUDE_PROJECT_DIR, then the payload's cwd.
# A .ai/ deeper in the tree does not count, and ".." segments are resolved
# first, so <root>/.ai/../README.md is outside. A target that is itself a
# symlink gets neither this exemption nor the plan-file ones below.
#
# Harness plan files are also allowed, with ".." resolved first:
# - Claude Code plan mode: $CLAUDE_CONFIG_DIR/plans/, default ~/.claude/plans/.
# - GitHub Copilot CLI: $COPILOT_HOME/session-state/<id>/plan.md, default
#   ~/.copilot/session-state/<id>/plan.md.
# - Hermes /plan: <root>/.hermes/plans/, with <root> as for .ai/.
# Other directories named plans, such as docs/plans/, are not allowed.
#
# The user asked when their latest prompt in the transcript names the file's
# basename, the basename without its extension (at least 4 characters), the
# word "markdown", or ".md", ignoring case. A short approval also counts: a
# prompt of at most 80 characters that starts with "yes", "ok", "go ahead" or
# a similar word, when the main thread's last assistant text before it names
# the file's basename. Inside a subagent, transcript_path
# is still the main session's transcript, so the user's prompt decides there
# too, not the delegating agent's brief.
#
# Hook protocol (Claude Code):
# - stdin: JSON envelope with tool_input.file_path, cwd and transcript_path.
# - stdout: a PreToolUse deny object, or nothing to allow.
# - exit code: always 0. Without a transcript prompt, use the matching
#   UserPromptSubmit prompt if available. Unknown prompts allow.

set -f
hooks_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd) || exit 0
read_json() {
  LC_ALL=C MODE=$1 awk -f "$hooks_dir/hook-json.awk" -f "$hooks_dir/user-prompt.awk" \
    -f "$hooks_dir/block_markdown_edits.awk" "${@:2}"
}

prompt_cache() {
  local config=${CLAUDE_CONFIG_DIR:-${HOME:+$HOME/.claude}}
  [ -n "$config" ] && [ -n "$1" ] || return 1
  printf '%s/dotai-steer/%s.json\n' "$config" "$1"
}

skip_prompt_history=${CLAUDE_CODE_SKIP_PROMPT_HISTORY:-}
case "${1:-}:$skip_prompt_history" in
  --forget-prompt:*|--remember-prompt:1)
    session=$(read_json session) || exit 0
    cache=$(prompt_cache "$session") || exit 0
    rm -f -- "$cache"
    exit 0
    ;;
esac

if [ "${1:-}" = --remember-prompt ]; then
  fields=$(read_json submit) || exit 0
  cache=$(prompt_cache "${fields%%$'\n'*}") || exit 0
  umask 077
  mkdir -p "${cache%/*}" || exit 0
  tmp=$(mktemp "$cache.XXXXXXXX") || exit 0
  if ! printf '%s\n' "${fields#*$'\n'}" >"$tmp" || ! mv -f "$tmp" "$cache"; then
    rm -f "$tmp"
  fi
  exit 0
fi

# lexical PATH: PATH with "." and ".." segments resolved, without touching disk.
lexical() {
  local part out='' IFS=/
  for part in $1; do
    case $part in '' | .) ;; ..) out=${out%/*} ;; *) out=$out/$part ;; esac
  done
  case $1 in /*) printf '%s\n' "${out:-/}" ;; *) printf '%s\n' "${out#/}" ;; esac
}

# absolute FILE CWD: FILE with "\\" as "/", made absolute against CWD and resolved.
absolute() {
  local path=${1//\\//}
  case $path in /* | [A-Za-z]:/*) ;; *) [ -n "$2" ] || return 1; path=$2/$path ;; esac
  lexical "$path"
}

# in_harness_plans FILE CWD: succeeds when FILE is a Claude Code or Copilot CLI plan file.
# ponytail: ignores Claude Code's plansDirectory setting and compares Windows
# drive paths (C:/) and Git Bash paths (/c/) as different; read settings.json
# and map drive letters if plans there get denied.
in_harness_plans() {
  local path claude copilot rest
  path=$(absolute "$1" "$2") || return 1
  claude=${CLAUDE_CONFIG_DIR:-${HOME:+$HOME/.claude}}
  copilot=${COPILOT_HOME:-${HOME:+$HOME/.copilot}}
  if [ -n "$claude" ]; then
    claude=$(lexical "${claude//\\//}")
    case $path in "${claude%/}"/plans/*) return 0 ;; esac
  fi
  if [ -n "$copilot" ]; then
    copilot=$(lexical "${copilot//\\//}")
    case $path in "${copilot%/}"/session-state/*) rest=${path#"${copilot%/}"/session-state/} ;; *) return 1 ;; esac
    case $rest in */*/*) ;; ?*/plan.md) return 0 ;; esac
  fi
  return 1
}

# in_project_allowed FILE CWD: succeeds when FILE is inside <root>/.ai/ or <root>/.hermes/plans/.
in_project_allowed() {
  local path dir rest='' rel root
  path=$(absolute "$1" "$2") || return 1
  dir=$path
  until [ -d "$dir" ]; do
    case $dir in */*) ;; *) return 1 ;; esac
    rest=/${dir##*/}$rest
    dir=${dir%/*}
    [ -n "$dir" ] || dir=/
  done
  if rel=$(git -C "$dir" rev-parse --show-prefix 2>/dev/null); then
    rel=$rel${rest#/}
  else
    root=${CLAUDE_PROJECT_DIR:-$2}
    [ -n "$root" ] || return 1
    root=$(lexical "${root//\\//}")
    case $path in "${root%/}"/*) rel=${path#"${root%/}"/} ;; *) return 1 ;; esac
  fi
  case $rel in .ai/* | .hermes/plans/*) return 0 ;; esac
  return 1
}

fields=$(read_json payload 2>/dev/null <<<"$(cat)") || exit 0
{ IFS= read -r transcript; IFS= read -r name; IFS= read -r file; IFS= read -r cwd
  IFS= read -r session; IFS= read -r prompt_id; } <<<"$fields"
# A symlink, even a dangling one, can point anywhere, so it gets no folder
# exemption. Directory symlinks need no check: git resolves them.
if ! { path=$(absolute "$file" "$cwd") && [ -L "$path" ]; }; then
  in_project_allowed "$file" "$cwd" && exit 0
  in_harness_plans "$file" "$cwd" && exit 0
fi
cache=
if [ "$skip_prompt_history" != 1 ]; then
  cache=$(prompt_cache "$session")
fi
[ -f "$transcript" ] || transcript=/dev/null
FILE_NAME=$name PROMPT_CACHE=$cache PROMPT_ID=$prompt_id read_json transcript "$transcript" 2>/dev/null
exit 0
