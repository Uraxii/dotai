# Load it after hook-json.awk, with LC_ALL=C. Prints standard input as one
# quoted JSON string. The text comes on standard input, not in an argument or
# the environment, so no size of text can fail the exec. Over JSON_MAX bytes,
# the text is cut on a character boundary and a notice line is added.

BEGIN {
  max = ENVIRON["JSON_MAX"] + 0
  while ((getline line) > 0) text = text (n++ ? "\n" : "") line
  if (max > 0 && length(text) > max) {
    text = substr(text, 1, max)
    sub(/[\300-\377][\200-\277]*$/, "", text)
    text = text "\n[The rest of this context was cut at " max " bytes.]"
  }
  printf "%s", jquote(text)
}
