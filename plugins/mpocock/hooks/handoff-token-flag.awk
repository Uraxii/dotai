# The JSON side of handoff-token-flag.sh. Load after hook-json.awk, with LC_ALL=C.
#
# MODE=payload reads the hook envelope on stdin and prints the transcript
# path, then the session id ("unknown" when absent). It exits 1 when either is
# missing or not a string.
#
# MODE=transcript reads the transcript file and prints the token count of the
# last usage line, or nothing when there is none. Claude records input plus
# both cache counts; Codex input_tokens already includes its cached tokens.

BEGIN {
  if (ENVIRON["MODE"] == "payload") {
    text = ""
    while ((getline line) > 0) text = text line "\n"
    if (!jparse(text) || JT[""] != "object") exit 1
    transcript = first_truthy("/transcript_path", "/transcriptPath")
    session = first_truthy("/session_id", "/sessionId")
    if (transcript == "" || JT[transcript] != "string") exit 1
    if (session != "" && JT[session] != "string") exit 1
    print jget(transcript)
    print (session == "" ? "unknown" : jget(session))
    exit 0
  }
}

# Only a line that names a usage key can set the count, and the last line
# that sets it wins, so the lines are read back from the end.
index($0, "usage") { LINES[++line_count] = $0 }

END {
  if (ENVIRON["MODE"] == "payload") exit
  for (i = line_count; i >= 1; i--) {
    if (usage_tokens(LINES[i])) {
      printf "%.0f\n", tokens
      exit
    }
  }
}

# Sets tokens and returns 1 when the line records usage.
function usage_tokens(line,    usage) {
  if (!jparse(line) || JT[""] != "object") return 0
  if (JT["/message"] == "object" && JT["/message/usage"] == "object" && jtruthy("/message/usage")) {
    tokens = count("/message/usage/input_tokens") + count("/message/usage/cache_read_input_tokens") \
      + count("/message/usage/cache_creation_input_tokens")
    return 1
  }
  if (JT["/payload"] != "object") return 0
  usage = ""
  if (jis("/type", "event_msg") && jis("/payload/type", "token_count") && JT["/payload/info"] == "object") {
    usage = "/payload/info/last_token_usage"
  } else if (jis("/type", "token_usage_record")) usage = "/payload/usage"
  if (usage == "" || JT[usage] != "object" || !jtruthy(usage)) return 0
  tokens = count(usage "/input_tokens")
  return 1
}

function first_truthy(first, second) {
  if (jtruthy(first)) return first
  if (jtruthy(second)) return second
  return ""
}

# A missing, null or false count reads as 0.
function count(path) {
  return JT[path] == "number" ? JR[path] + 0 : 0
}
