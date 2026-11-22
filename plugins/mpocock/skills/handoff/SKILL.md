---
name: handoff
description: Compact the current conversation into a handoff document for another agent to pick up.
argument-hint: "What will the next session be used for?"
disable-model-invocation: true
compatibility: Needs write access to a handoffs directory. Run it by hand; the model does not load it.
license: MIT
metadata:
  version: 1.1.0
  author: Matt Pocock
  homepage: https://github.com/Uraxii/dotai
  source: https://github.com/mattpocock/skills/tree/abeeaf95660ba9e8b7c753eb38f441ca707a8823/skills/productivity/handoff
---

Write a handoff document summarizing the objective plus the next-session focus.

Write handoffs into the directory the user's or project's instructions name for handoffs. If they name none, use `.handoffs/` at the project root.

When this handoff is one link in a sequence, capture the whole workstream: overarching goal, full task list with done / current / remaining status, and every decision, convention, or constraint agreed up front that binds all tasks. That is carry-forward context and it must survive the entire chain.

Include a "suggested skills" section in the document, naming which skills the next agent should call the Skill tool for.

Do not duplicate content already captured in other artifacts (specs, plans, ADRs, issues, commits, diffs). Reference them by path or URL instead.

Redact any sensitive information, such as API keys, passwords, or personally identifiable information.

If the user passed arguments, treat them as a description of what the next session will focus on and tailor the doc accordingly.

## Present the handoff

After you create or update the handoff file, do these steps in every session, local or cloud. Do not use a different format.

1. Summarize the handoff content in chat. Give the objective, the next-session focus, and the open items in a few short lines.
2. Send the file to the user with a tool that sends files to the user, such as `SendUserFile`, so the user can download it. If no such tool is available, or sending fails, tell the user in one line.
3. End your message with the file's full absolute path in a fenced code block. Most harnesses show a copy button on a code block. Put nothing after the code block.

Example of the end of the message:

````
Handoff: auth migration. Token refresh is done. Next session moves the session store to Redis. Open item: decide the TTL for remember-me tokens.

```
/home/user/project/.ai/.handoffs/auth-migration.md
```
````
