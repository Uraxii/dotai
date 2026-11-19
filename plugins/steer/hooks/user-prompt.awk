# Turn-boundary test shared by the steer hooks. Load after hook-json.awk.
#
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
