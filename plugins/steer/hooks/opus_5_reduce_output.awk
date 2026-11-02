# The JSON side of opus_5_reduce_output.sh. Load after hook-json.awk, with LC_ALL=C.
#
# MODE=payload reads the Stop envelope on stdin. It prints 1 or 0 for
# stop_hook_active, then the transcript path or an empty line. It exits 1 when
# the envelope is not a JSON object, and 2 when transcript_path is truthy but
# not a string.
#
# MODE=transcript reads the transcript file. It prints the model of the last
# main-agent reply ("-" if none), then the turn: "unknown" when no real user
# prompt bounds it, else "mutated" or "clean". It exits 1 when the entry it
# needs is malformed.

BEGIN {
  if (ENVIRON["MODE"] == "payload") {
    text = ""
    while ((getline line) > 0) text = text line "\n"
    if (!jparse(text) || JT[""] != "object") exit 1
    print jtruthy("/stop_hook_active") ? 1 : 0
    if (!jtruthy("/transcript_path")) print ""
    else if (JT["/transcript_path"] != "string") exit 2
    else print jget("/transcript_path")
    exit 0
  }
  split("Write Edit MultiEdit NotebookEdit Agent Task SendMessage", list, " ")
  for (i in list) MUTATING_TOOLS[list[i]] = 1
  split("rm rmdir mv cp mkdir touch install ln tee dd truncate chmod chown patch", list, " ")
  for (i in list) MUTATING_COMMANDS[list[i]] = 1
  split("sed perl ruby", list, " ")
  for (i in list) IN_PLACE_EDITORS[list[i]] = 1
  split("sudo env command nohup time xargs", list, " ")
  for (i in list) COMMAND_WRAPPERS[list[i]] = 1
  split("-C -R -c --repo --git-dir --work-tree", list, " ")
  for (i in list) GLOBAL_OPTIONS_TAKING_A_VALUE[list[i]] = 1
  # Mutating verbs that live one or two tokens past the program name.
  prefix_count = split("git add|git am|git apply|git cherry-pick|git checkout|git clean|git commit|git merge|" \
    "git mv|git push|git rebase|git reset|git restore|git revert|git rm|git stash|git switch|git tag|" \
    "git branch -D|git branch -d|git branch -M|git branch -m|" \
    "git worktree add|git worktree remove|git worktree prune|" \
    "gh pr create|gh pr merge|gh pr close|gh pr edit|gh pr comment|gh repo create|gh release create", PREFIXES, "|")
  model = "-"
}

# Only entries typed user or assistant can bound the turn or carry tool
# calls. The turn is the tail after the last real user prompt, so the lines
# are read back from the end.
index($0, "\"user\"") || index($0, "\"assistant\"") { LINES[++line_count] = $0 }

END {
  if (ENVIRON["MODE"] == "payload") exit
  for (i = line_count; i >= 1 && !(model_found && prompt_seen); i--) {
    if (prompt_seen && !index(LINES[i], "\"assistant\"")) continue
    if (!jparse(LINES[i]) || JT[""] != "object" || jtruthy("/isSidechain")) continue
    if (jis("/type", "assistant")) {
      if (!model_found) {
        model_found = 1
        if (JT["/message"] == "object" && jtruthy("/message/model")) {
          if (JT["/message/model"] != "string") exit 1
          model = jget("/message/model")
        }
      }
      if (!prompt_seen && JT["/message"] == "object" && JT["/message/content"] == "array") {
        for (b = 0; b < JN["/message/content"]; b++) {
          block = "/message/content/" b
          if (JT[block] == "object" && jis(block "/type", "tool_use")) tool_use(block)
        }
      }
    } else if (!prompt_seen && real_user_prompt()) prompt_seen = 1
  }
  if (prompt_seen && broken_turn) exit 1
  print model
  print (!prompt_seen ? "unknown" : mutated ? "mutated" : "clean")
}

# A tool result and a harness injection (isMeta) are type "user" too, but
# only a typed prompt bounds the turn.
function real_user_prompt(    b) {
  if (!jis("/type", "user") || jtruthy("/isMeta") || JT["/message"] != "object") return 0
  if (JT["/message/content"] == "string") return 1
  if (JT["/message/content"] != "array") return 0
  for (b = 0; b < JN["/message/content"]; b++) {
    if (JT["/message/content/" b] == "object" && jis("/message/content/" b "/type", "text")) return 1
  }
  return 0
}

# Agent, Task and SendMessage count as mutations because a delegate's own
# edits never reach this transcript. Bash is classified by its command.
function tool_use(block,    name) {
  if (JT[block "/name"] != "string") return
  name = jget(block "/name")
  if (name in MUTATING_TOOLS) mutated = 1
  else if (name == "Bash" && jtruthy(block "/input")) {
    if (JT[block "/input"] != "object") broken_turn = 1
    else if (JT[block "/input/command"] == "string" && command_mutates(jget(block "/input/command"))) mutated = 1
  }
}

# Bash is classified by a DENYLIST of mutating shapes, not an allowlist of
# safe ones: a wrong skip costs one missing recap, while a wrong recap is the
# bug this gate exists to fix. So an unknown command reads as clean.
function command_mutates(command,    n, i, segment) {
  gsub(/&&|\|\||;|\||\n/, "\034", command)
  n = split(command, SEGMENTS, "\034")
  for (i = 1; i <= n; i++) {
    segment = without_discards(SEGMENTS[i])
    if (redirects_to_file(segment) || segment_mutates(segment)) return 1
  }
  return 0
}

# A redirect to /dev/null discards output rather than writing it, so it is
# removed before the write check. Only the discard is excused.
function without_discards(s,    out, after) {
  out = ""
  while (match(s, />>?[ \t\n\r\f\v]*\/dev\/null/)) {
    after = substr(s, RSTART + RLENGTH, 1)
    if (after != "" && (after ~ /[A-Za-z0-9_]/ || after > "\177")) {
      out = out substr(s, 1, RSTART)
      s = substr(s, RSTART + 1)
    } else {
      out = out substr(s, 1, RSTART - 1)
      s = substr(s, RSTART + RLENGTH)
    }
  }
  return out s
}

# A > or >> into a file. A trailing & is a descriptor dup (2>&1, >&2), and a
# > after - = < > or ! is part of another operator (->, >=).
function redirects_to_file(s,    p, len, next_char) {
  len = length(s)
  for (p = 1; p <= len; p++) {
    if (substr(s, p, 1) != ">") continue
    if (p > 1 && index("-=<>!", substr(s, p - 1, 1))) continue
    next_char = substr(s, p + 1, 1)
    if (next_char == ">" || next_char == "" || !index("&=", next_char)) return 1
  }
  return 0
}

function segment_mutates(segment,    n, start, program, i, p, k, parts, argument_count) {
  n = shell_words(segment)
  start = 1
  while (start <= n && (basename(WORDS[start]) in COMMAND_WRAPPERS || index(WORDS[start], "="))) start++
  if (start > n) return 0
  program = basename(WORDS[start])
  if (program in MUTATING_COMMANDS) return 1
  if (program in IN_PLACE_EDITORS) {
    for (i = start + 1; i <= n; i++) if (substr(WORDS[i], 1, 2) == "-i") return 1
  }
  # Global options sit between a program and its verb, so `git -C <dir> push`
  # reaches the same verdict as `git push`. These take a value, so both go.
  i = start + 1
  while (i <= n && substr(WORDS[i], 1, 1) == "-") i += (WORDS[i] in GLOBAL_OPTIONS_TAKING_A_VALUE) ? 2 : 1
  for (p = 1; p <= prefix_count; p++) {
    argument_count = split(PREFIXES[p], parts, " ")
    if (parts[1] != program) continue
    for (k = 2; k <= argument_count; k++) if (i + k - 2 > n || WORDS[i + k - 2] != parts[k]) break
    if (k > argument_count) return 1
  }
  return 0
}

function basename(path,    n, i, parts) {
  n = split(path, parts, "/")
  for (i = n; i >= 1; i--) if (parts[i] != "" && parts[i] != ".") return parts[i]
  return ""
}

# Shell word splitting into WORDS, as Python shlex.split does it. An unclosed
# quote or a trailing backslash falls back to plain whitespace splitting.
function shell_words(s,    n, i, len, c, state, escaped_from, word, quoted, count) {
  n = 0
  state = " "
  word = ""
  quoted = 0
  len = length(s)
  for (i = 1; i <= len; i++) {
    c = substr(s, i, 1)
    if (state == "\\") {
      if (escaped_from == "\"" && c != "\\" && c != "\"") word = word "\\"
      word = word c
      state = escaped_from
    } else if (state == "'" || state == "\"") {
      if (c == state) state = "a"
      else if (c == "\\" && state == "\"") {
        escaped_from = state
        state = "\\"
      } else word = word c
    } else if (c == " " || c == "\t" || c == "\r" || c == "\n") {
      if (state == "a" && (word != "" || quoted)) WORDS[++n] = word
      word = ""
      quoted = 0
      state = " "
    } else if (c == "\\") {
      escaped_from = "a"
      state = "\\"
    } else if (c == "'" || c == "\"") {
      quoted = 1
      state = c
    } else {
      word = word c
      state = "a"
    }
  }
  if (state == "\\" || state == "'" || state == "\"") {
    count = split(s, PARTS, /[ \t\n\r\f\v]+/)
    n = 0
    for (i = 1; i <= count; i++) if (PARTS[i] != "") WORDS[++n] = PARTS[i]
    return n
  }
  if (state == "a" && (word != "" || quoted)) WORDS[++n] = word
  return n
}
