# The text side of inject_instructions.sh. Load after hook-json.awk, with LC_ALL=C.
# Reads the instruction file named by FILE and prints it for HARNESS and EVENT.
# Exits 3 when the file is not valid UTF-8.

BEGIN {
  path = ENVIRON["FILE"]
  harness = ENVIRON["HARNESS"]
  event = ENVIRON["EVENT"]
  text = ""
  while ((status = (getline line < path)) > 0) {
    if (!utf8(line)) exit 3
    text = text line "\n"
  }
  if (status < 0) exit 4
  # Python's strip() after its newline translation.
  gsub(/\r\n/, "\n", text)
  gsub(/\r/, "\n", text)
  sub(/^[ \t\n\f\v]+/, "", text)
  sub(/[ \t\n\f\v]+$/, "", text)
  if (text == "") exit 0
  if (harness == "codex" || (harness == "claude" && event == "SubagentStart")) {
    print "{\"hookSpecificOutput\": {\"hookEventName\": " jquote(event) ", \"additionalContext\": " jquote(text) "}}"
  } else if (harness == "copilot") print "{\"additionalContext\": " jquote(text) "}"
  else print text
}

function utf8(s) {
  return s ~ /^([\001-\177]|[\302-\337][\200-\277]|\340[\240-\277][\200-\277]|[\341-\354\356\357][\200-\277][\200-\277]|\355[\200-\237][\200-\277]|\360[\220-\277][\200-\277][\200-\277]|[\361-\363][\200-\277][\200-\277][\200-\277]|\364[\200-\217][\200-\277][\200-\277])*$/
}
