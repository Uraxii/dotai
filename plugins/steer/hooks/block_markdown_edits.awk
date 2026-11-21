# The JSON side of block_markdown_edits.sh. Load after hook-json.awk and
# user-prompt.awk, with LC_ALL=C.
#
# MODE=payload reads the PreToolUse envelope on stdin. When the target is a
# markdown file it prints the transcript path, the file's basename, the
# file_path and the payload's cwd, one per line, and exits 0. It exits 1 for
# anything else: not JSON, no file_path, or a file that is not markdown.
#
# MODE=transcript reads the transcript file, with FILE_NAME set to that
# basename. It prints the deny output when the user's latest prompt names
# none of the unlock words and is not a short approval of an assistant
# message that names the file. It prints nothing when no prompt of the
# user's is found.

BEGIN {
  if (ENVIRON["MODE"] == "payload") {
    text = ""
    while ((getline line) > 0) text = text line "\n"
    if (!jparse(text) || JT[""] != "object" || JT["/tool_input/file_path"] != "string") exit 1
    path = jget("/tool_input/file_path")
    name = path
    sub(/.*[\/\\]/, "", name)
    if (tolower(name) !~ /\.(md|markdown|mdx)$/) exit 1
    print (JT["/transcript_path"] == "string" ? jget("/transcript_path") : "")
    print name
    print path
    print (JT["/cwd"] == "string" ? jget("/cwd") : "")
    exit 0
  }
}

index($0, "\"user\"") || index($0, "\"assistant\"") { LINES[++line_count] = $0 }

END {
  if (ENVIRON["MODE"] == "payload") exit
  for (i = line_count; i >= 1; i--) {
    if (!jparse(LINES[i]) || JT[""] != "object" || jtruthy("/isSidechain")) continue
    if (human_prompt()) break
  }
  if (i < 1) exit
  prompt = tolower(message_text())
  name = ENVIRON["FILE_NAME"]
  stem = name
  sub(/\.[^.]*$/, "", stem)
  if (index(prompt, tolower(name)) || index(prompt, "markdown") || index(prompt, ".md")) exit
  if (length(stem) >= 4 && index(prompt, tolower(stem))) exit
  if (approval(prompt) && index(tolower(assistant_text_before(i)), tolower(name))) exit
  reason = "Blocked: the user's latest message does not ask for markdown edits, so " name " stays as it is. " \
    "Markdown outside the project's .ai/ folder needs the user's request. Ask the user in chat before you edit it. " \
    "If the user names the file, says \"markdown\", or answers yes to your question that names the file, the edit is allowed. " \
    "Notes, plans and handoffs belong in .ai/ at the project root, where markdown edits are always allowed. " \
    "Keep your notes in memory or in .ai/, not in this file. " \
    "If you think a lasting rule is necessary, suggest it to the user in chat as an AGENTS.md entry, a lint, or a test. " \
    "Name which one, and tell the user which mistake that rule prevents."
  printf "{\"hookSpecificOutput\":{\"hookEventName\":\"PreToolUse\",\"permissionDecision\":\"deny\",\"permissionDecisionReason\":%s}}\n", jquote(reason)
}

# The words the user typed. A task notification (a background agent's report)
# is a real prompt by real_user_prompt, but the user did not write it. Older
# transcripts carry no origin, so only a non-human origin is excluded.
function human_prompt() {
  return real_user_prompt() && (JT["/origin/kind"] != "string" || jis("/origin/kind", "human"))
}

function message_text(    b, out) {
  if (JT["/message/content"] == "string") return jget("/message/content")
  out = ""
  for (b = 0; b < JN["/message/content"]; b++) {
    if (jis("/message/content/" b "/type", "text")) out = out jget("/message/content/" b "/text") "\n"
  }
  return out
}

# A short yes to the assistant's question, such as "yes, go ahead". PROMPT is
# lowercase. "yesterday" and "okra" are not approvals.
function approval(prompt) {
  gsub(/^[ \t\r\n]+|[ \t\r\n]+$/, "", prompt)
  return length(prompt) <= 80 && \
    prompt ~ /^(yes|y|yep|yeah|sure|ok|okay|go ahead|do it|approved|please do)([^a-z]|$)/
}

# The text of the main thread's last assistant entry with text before line
# I, within the turn that line I ends. Tool calls carry no text blocks.
function assistant_text_before(i,    j) {
  for (j = i - 1; j >= 1; j--) {
    if (!jparse(LINES[j]) || JT[""] != "object" || jtruthy("/isSidechain")) continue
    if (real_user_prompt()) return ""
    if (jis("/type", "assistant") && message_text() != "") return message_text()
  }
  return ""
}
