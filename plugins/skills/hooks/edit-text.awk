# Load it after hook-json.awk, with LC_ALL=C and JSON_MODE empty. Prints the
# text a Claude Write, Edit or MultiEdit writes: tool_input.content,
# tool_input.new_string, and the new_string of each tool_input.edits item.

BEGIN {
  while ((getline line) > 0) text = text line "\n"
  if (!jparse(text)) exit 0
  printf "%s\n%s\n", jget("/tool_input/content"), jget("/tool_input/new_string")
  for (i = 0; i < JN["/tool_input/edits"]; i++) printf "%s\n", jget("/tool_input/edits/" i "/new_string")
}
