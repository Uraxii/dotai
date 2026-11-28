# Load it after hook-json.awk, with LC_ALL=C, JSON_MODE empty and HARNESS set
# to claude, codex or copilot. Parses the hook input once and prints the cwd,
# the session id and the edit's path, one per line, then the text the edit
# writes: for Claude, tool_input.content, tool_input.new_string and the
# new_string of each tool_input.edits item; for Codex, the whole patch.
# Prints nothing for malformed JSON, or for a cwd or path that holds a
# newline, because that is not one directory or file.

BEGIN {
  while ((getline line) > 0) text = text line "\n"
  if (!jparse(text)) exit 0
  harness = ENVIRON["HARNESS"]
  cwd = jget("/cwd")
  if (harness == "copilot") {
    session = jget("/sessionId")
    # toolArgs is a JSON object, or a string that holds one.
    if (JT["/toolArgs"] != "string") path = jget("/toolArgs/path")
    else if (jparse(jdecode(JR["/toolArgs"]))) path = jget("/path")
  } else session = jget("/session_id")
  if (harness == "claude") path = jget("/tool_input/file_path")
  if (index(cwd path, "\n")) exit 0
  # A newline would split the session line. A space keeps the id unusable.
  gsub(/\n/, " ", session)
  printf "%s\n%s\n%s\n", cwd, session, path
  if (harness == "codex") printf "%s\n", jget("/tool_input/command")
  if (harness != "claude") exit 0
  printf "%s\n%s\n", jget("/tool_input/content"), jget("/tool_input/new_string")
  for (i = 0; i < JN["/tool_input/edits"]; i++) printf "%s\n", jget("/tool_input/edits/" i "/new_string")
}
