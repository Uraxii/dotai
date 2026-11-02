# The JSON side of lifecycle_context.sh. Load after hook-json.awk, with LC_ALL=C.
# Joins the instructions file, the graph context from hook-augment's output
# file, and the reminder, and prints the one context envelope for the harness.
# Inputs come from the environment: HARNESS, EVENT, INSTRUCTIONS (a path),
# AUGMENT (a path) and REMINDER.

BEGIN {
  harness = ENVIRON["HARNESS"]
  event = ENVIRON["EVENT"]
  text = strip(slurp(ENVIRON["INSTRUCTIONS"]))
  context = graph_context(slurp(ENVIRON["AUGMENT"]))
  if (context != "") text = text (text == "" ? "" : "\n\n") context
  if (ENVIRON["REMINDER"] != "") text = text (text == "" ? "" : "\n\n") ENVIRON["REMINDER"]
  if (text == "") exit 0
  if (harness == "claude") {
    print "{\"hookSpecificOutput\": {\"hookEventName\": " jquote(event) ", \"additionalContext\": " jquote(text) "}}"
  } else print "{\"additionalContext\": " jquote(text) "}"
}

function slurp(path,    text, line) {
  text = ""
  while ((getline line < path) > 0) text = text line "\n"
  close(path)
  return text
}

# Python's strip() after its newline translation.
function strip(text) {
  gsub(/\r\n/, "\n", text)
  gsub(/\r/, "\n", text)
  sub(/^[ \t\n\f\v]+/, "", text)
  sub(/[ \t\n\f\v]+$/, "", text)
  return text
}

function graph_context(output,    base) {
  if (!jparse(output) || JT[""] != "object") return ""
  base = ""
  if (harness == "claude") {
    base = "/hookSpecificOutput"
    if (JT[base] != "object") return ""
  }
  return JT[base "/additionalContext"] == "string" ? jget(base "/additionalContext") : ""
}
