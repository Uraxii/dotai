---
name: principle-output-to-user
description: Use every time you write a reply the human reads, before sending it, and whenever a reply is about to run past a few lines, narrate progress, bury a path or command mid-sentence, or hand the user something to paste into another session such as a handoff path. Caps each turn at one short outcome-first reply and puts every copy-paste value in a code block on its own line.
---

# Output to user

Human read between other things. One reply per turn, outcome first, then
stop. Anything the human will copy goes in a block, full path, one per line.

## Length

- Under 4 lines per reply, code and tool calls excluded. One line if it fit;
  one word best. Extra detail only when asked or when you found an issue.
- Lead with the outcome. First sentence = what happened or what was found.
- One user-facing reply per TURN. No preamble ("Here is", "Based on"), no
  postamble (recap, "what I did"), no progress narration between tool calls.
  Stop once outcome stated.
- Never narrate options not taken or re-derive facts already established.
  Thinking can run long; output stay short.

## Copy-paste values

- Paths, commands, URLs, tokens, values: own line, code block or list, never
  mid-sentence. Data first, then at most one short note.
- Paths always full local paths. Never relative, never `~`, never bare
  filename.
- Handoff, transcript, report, or any artifact the user open in another
  session: the absolute path alone in a code block, so it paste straight in.
- Sequence of commands: one fenced block, in run order, nothing between steps.

## Shape

- Prefer a visual or diagram for complex information over a paragraph.
- Yes/no question get "Yes." or "No." plus at most one clause.

## Examples

- "what was the last photo?" -> send photo + <=5 words.
- "is X prime?" -> "Yes."
- "where is the auth key?" -> two paths in a code block, one line each,
  nothing else.
- end of a handoff -> the handoff file's absolute path in a code block,
  nothing else.

## Boundaries

Register (caveman, persona exceptions) and AI-tell removal live in `unslop`.
Bulk that would swamp the reply (logs, many files) goes to a subagent per
`principle-guard-the-context-window`; the reply carry the summary. Rules are
silent constraints: never announce compliance, never spawn a pass to check one.
