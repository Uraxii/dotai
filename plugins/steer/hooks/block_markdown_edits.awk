# The JSON side of block_markdown_edits.sh. Load after hook-json.awk and
# user-prompt.awk, with LC_ALL=C.
#
# MODE=payload reads the PreToolUse envelope on stdin. When the target is a
# markdown file it prints the transcript path, then the file's basename, and
# exits 0. It exits 1 for anything else: not JSON, no file_path, or a file
# that is not markdown.
#
# MODE=transcript reads the transcript file, with FILE_NAME set to that
# basename. It prints the deny output when the user's latest prompt names
# none of the unlock words, and prints nothing when it names one or when no
# prompt of the user's is found.

BEGIN {
  if (ENVIRON["MODE"] == "payload") {
    text = ""
    while ((getline line) > 0) text = text line "\n"
    if (!jparse(text) || JT[""] != "object" || JT["/tool_input/file_path"] != "string") exit 1
    name = jget("/tool_input/file_path")
    sub(/.*[\/\\]/, "", name)
    if (tolower(name) !~ /\.(md|markdown|mdx)$/) exit 1
    print (JT["/transcript_path"] == "string" ? jget("/transcript_path") : "")
    print name
    exit 0
  }
}

index($0, "\"user\"") { LINES[++line_count] = $0 }

END {
  if (ENVIRON["MODE"] == "payload") exit
  for (i = line_count; i >= 1; i--) {
    if (!jparse(LINES[i]) || JT[""] != "object" || jtruthy("/isSidechain")) continue
    if (human_prompt()) break
  }
  if (i < 1) exit
  prompt = tolower(prompt_text())
  name = ENVIRON["FILE_NAME"]
  stem = name
  sub(/\.[^.]*$/, "", stem)
  if (index(prompt, tolower(name)) || index(prompt, "markdown") || index(prompt, ".md")) exit
  if (length(stem) >= 4 && index(prompt, tolower(stem))) exit
  reason = "Blocked: the user's latest message does not ask for markdown edits, so " name " stays as it is. " \
    "Ask the user in chat before you edit it. If the user names the file or says \"markdown\", the edit is allowed."
  printf "{\"hookSpecificOutput\":{\"hookEventName\":\"PreToolUse\",\"permissionDecision\":\"deny\",\"permissionDecisionReason\":%s}}\n", jquote(reason)
}

# The words the user typed. A task notification (a background agent's report)
# is a real prompt by real_user_prompt, but the user did not write it. Older
# transcripts carry no origin, so only a non-human origin is excluded.
function human_prompt() {
  return real_user_prompt() && (JT["/origin/kind"] != "string" || jis("/origin/kind", "human"))
}

function prompt_text(    b, out) {
  if (JT["/message/content"] == "string") return jget("/message/content")
  out = ""
  for (b = 0; b < JN["/message/content"]; b++) {
    if (jis("/message/content/" b "/type", "text")) out = out jget("/message/content/" b "/text") "\n"
  }
  return out
}
