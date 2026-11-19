#!/usr/bin/env bash
# block_markdown_edits: PreToolUse hook that denies Write, Edit and MultiEdit
# on a markdown file (.md, .markdown, .mdx, any case) unless the user asked.
#
# Wired in the plugin's hooks/claude-hooks.json. It needs only bash and awk,
# so Git Bash runs it on Windows. block_markdown_edits.awk reads the JSON.
#
# The user asked when their latest prompt in the transcript names the file's
# basename, the basename without its extension (at least 4 characters), the
# word "markdown", or ".md", ignoring case. Inside a subagent, transcript_path
# is still the main session's transcript, so the user's prompt decides there
# too, not the delegating agent's brief.
#
# Hook protocol (Claude Code):
# - stdin: JSON envelope with tool_input.file_path and transcript_path.
# - stdout: a PreToolUse deny object, or nothing to allow.
# - exit code: always 0. Bad JSON, a missing transcript, no user prompt or
#   any error allows. Never crash the session.

hooks_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd) || exit 0
read_json() {
  LC_ALL=C MODE=$1 awk -f "$hooks_dir/hook-json.awk" -f "$hooks_dir/user-prompt.awk" \
    -f "$hooks_dir/block_markdown_edits.awk" "${@:2}"
}

fields=$(read_json payload 2>/dev/null <<<"$(cat)") || exit 0
transcript=${fields%%$'\n'*}
[ -n "$transcript" ] && [ -f "$transcript" ] || exit 0
FILE_NAME=${fields#*$'\n'} read_json transcript "$transcript" 2>/dev/null
exit 0
