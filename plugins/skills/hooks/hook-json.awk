# JSON reader and writer for this plugin's hooks. POSIX awk. Run it with
# LC_ALL=C, so strings are bytes. The same file ships in every plugin that
# needs it, because a plugin cannot read another plugin's files; a test keeps
# the copies identical.
#
# jparse(text) reads one JSON value and returns 1, or 0 for malformed JSON:
#   JT[path]  node type: object, array, string, number, true, false, null
#   JR[path]  string content, still escaped, or the number text
#   JN[path]  member count of an object or array
# The root path is "". Each step adds "/key" or "/index".
#
# Shell scripts can also run this file on its own:
# - JSON_MODE=get JSON_PATH=/path reads standard input and prints that value
#   as `jq -r '.path // empty'` would. JSON_VIA=/sub first goes into /sub,
#   parsing /sub as JSON when it is a string, as `fromjson?` would.
# - JSON_MODE=quote JSON_TEXT=... prints JSON_TEXT as a quoted JSON string.

BEGIN {
  if (ENVIRON["JSON_MODE"] == "get") {
    jtext = ""
    while ((getline jline) > 0) jtext = jtext jline "\n"
    if (!jparse(jtext)) exit 0
    jbase = ENVIRON["JSON_VIA"]
    if (jbase != "") {
      if (JT[jbase] == "string") {
        if (!jparse(jdecode(JR[jbase]))) exit 0
        jbase = ""
      } else if (JT[jbase] != "object") exit 0
    }
    printf "%s", jget(jbase ENVIRON["JSON_PATH"])
    exit 0
  }
  if (ENVIRON["JSON_MODE"] == "quote") {
    printf "%s", jquote(ENVIRON["JSON_TEXT"])
    exit 0
  }
}

function jparse(text,    n, i, inside, raw, run, part, rest) {
  split("", JT)
  split("", JR)
  split("", JN)
  split("", TT)
  split("", TV)
  jnt = 0
  # Splitting on quotes makes the odd parts string content, so the scan is
  # linear even for a long line. A part that ends in an odd run of
  # backslashes ends at an escaped quote, so the string goes on.
  # BWK awk (macOS) also splits on newline. A raw newline is whitespace
  # outside a string and invalid inside one, and so is a carriage return.
  if (index(text, "\n")) gsub(/\n/, "\r", text)
  n = split(text, JP, "\"")
  inside = 0
  for (i = 1; i <= n; i++) {
    part = JP[i]
    if (!inside) {
      if (!jlex(part)) return 0
      inside = 1
      raw = ""
      continue
    }
    # No quote follows the last part, so a string still open there is unclosed.
    if (i == n) return 0
    raw = raw part
    run = 0
    if (substr(part, length(part), 1) == "\\") {
      match(part, /\\+$/)
      run = RLENGTH
    }
    if (run % 2 == 1) {
      raw = raw "\""
      continue
    }
    if (raw ~ /[\001-\037]/) return 0
    if (index(raw, "\\")) {
      rest = raw
      gsub(/\\(["\\\/bfnrt]|u[0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f])/, "", rest)
      if (index(rest, "\\")) return 0
    }
    TT[++jnt] = "s"
    TV[jnt] = raw
    inside = 0
  }
  jti = 1
  if (!jvalue("")) return 0
  return jti == jnt + 1
}

# Tokens between strings: punctuation, numbers, true, false and null.
function jlex(seg,    j, len, c) {
  j = 1
  len = length(seg)
  while (j <= len) {
    c = substr(seg, j, 1)
    if (c == " " || c == "\t" || c == "\n" || c == "\r") j++
    else if (index("{}[]:,", c)) {
      TT[++jnt] = c
      j++
    } else if (match(substr(seg, j), /^-?(0|[1-9][0-9]*)(\.[0-9]+)?([eE][+-]?[0-9]+)?/)) {
      TT[++jnt] = "n"
      TV[jnt] = substr(seg, j, RLENGTH)
      j += RLENGTH
    } else if (substr(seg, j, 4) == "true" || substr(seg, j, 4) == "null") {
      TT[++jnt] = substr(seg, j, 4)
      j += 4
    } else if (substr(seg, j, 5) == "false") {
      TT[++jnt] = "false"
      j += 5
    } else return 0
  }
  return 1
}

function jvalue(path,    t) {
  t = TT[jti]
  if (t == "{") return jobject(path)
  if (t == "[") return jarray(path)
  if (t == "s") JT[path] = "string"
  else if (t == "n") JT[path] = "number"
  else if (t == "true" || t == "false" || t == "null") JT[path] = t
  else return 0
  JR[path] = TV[jti++]
  return 1
}

function jobject(path,    count) {
  JT[path] = "object"
  jti++
  count = 0
  if (TT[jti] == "}") {
    jti++
    JN[path] = 0
    return 1
  }
  while (1) {
    if (TT[jti] != "s" || TT[jti + 1] != ":") return 0
    jti += 2
    if (!jvalue(path "/" jdecode(TV[jti - 2]))) return 0
    count++
    if (TT[jti] == "}") {
      jti++
      JN[path] = count
      return 1
    }
    if (TT[jti++] != ",") return 0
  }
}

function jarray(path,    count) {
  JT[path] = "array"
  jti++
  count = 0
  if (TT[jti] == "]") {
    jti++
    JN[path] = 0
    return 1
  }
  while (1) {
    if (!jvalue(path "/" count++)) return 0
    if (TT[jti] == "]") {
      jti++
      JN[path] = count
      return 1
    }
    if (TT[jti++] != ",") return 0
  }
}

# The value at path as `jq -r '// empty'` prints it: a string decoded, a
# number as written, true as "true", and false, null or a missing value as "".
# Only the emptiness of an object or array matters to the hooks.
function jget(path,    t) {
  t = JT[path]
  if (t == "string") return jdecode(JR[path])
  if (t == "number") return JR[path]
  if (t == "true") return "true"
  if (t == "object" || t == "array") return t
  return ""
}

# True when path holds the string value.
function jis(path, value) {
  return JT[path] == "string" && jdecode(JR[path]) == value
}

# Python truthiness of the value at path.
function jtruthy(path,    t) {
  t = JT[path]
  if (t == "true") return 1
  if (t == "string") return JR[path] != ""
  if (t == "number") return JR[path] + 0 != 0
  if (t == "object" || t == "array") return JN[path] > 0
  return 0
}

function jdecode(s,    out, i, c, code, low) {
  if (!index(s, "\\")) return s
  out = ""
  while ((i = index(s, "\\")) > 0) {
    out = out substr(s, 1, i - 1)
    c = substr(s, i + 1, 1)
    if (c == "u") {
      code = jhex(substr(s, i + 2, 4))
      s = substr(s, i + 6)
      if (code >= 55296 && code <= 56319 && substr(s, 1, 2) == "\\u") {
        low = jhex(substr(s, 3, 4))
        if (low >= 56320 && low <= 57343) {
          code = 65536 + (code - 55296) * 1024 + (low - 56320)
          s = substr(s, 7)
        }
      }
      out = out jutf8(code)
      continue
    }
    if (c == "n") out = out "\n"
    else if (c == "t") out = out "\t"
    else if (c == "r") out = out "\r"
    else if (c == "b") out = out sprintf("%c", 8)
    else if (c == "f") out = out sprintf("%c", 12)
    else out = out c
    s = substr(s, i + 2)
  }
  return out s
}

function jhex(h,    v, i) {
  v = 0
  for (i = 1; i <= 4; i++) v = v * 16 + index("0123456789abcdef", tolower(substr(h, i, 1))) - 1
  return v
}

# UTF-8 bytes for a code point. awk strings cannot hold NUL, so U+0000 is dropped.
function jutf8(code) {
  if (code == 0) return ""
  if (code < 128) return sprintf("%c", code)
  if (code < 2048) return sprintf("%c%c", 192 + int(code / 64), 128 + code % 64)
  if (code < 65536) return sprintf("%c%c%c", 224 + int(code / 4096), 128 + int(code / 64) % 64, 128 + code % 64)
  return sprintf("%c%c%c%c", 240 + int(code / 262144), 128 + int(code / 4096) % 64, 128 + int(code / 64) % 64, 128 + code % 64)
}

# s as a quoted JSON string.
function jquote(s,    out, c) {
  out = ""
  while (match(s, /[\\"\001-\037]/)) {
    c = substr(s, RSTART, 1)
    out = out substr(s, 1, RSTART - 1)
    if (c == "\\") out = out "\\\\"
    else if (c == "\"") out = out "\\\""
    else if (c == "\n") out = out "\\n"
    else if (c == "\r") out = out "\\r"
    else if (c == "\t") out = out "\\t"
    else out = out sprintf("\\u%04x", index("\001\002\003\004\005\006\007\010\011\012\013\014\015\016\017\020\021\022\023\024\025\026\027\030\031\032\033\034\035\036\037", c))
    s = substr(s, RSTART + 1)
  }
  return "\"" out s "\""
}
