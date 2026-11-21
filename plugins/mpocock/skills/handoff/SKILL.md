---
name: handoff
description: Compact the current conversation into a handoff document for another agent to pick up.
argument-hint: "What will the next session be used for?"
disable-model-invocation: true
compatibility: Needs write access to a handoffs directory. Run it by hand; the model does not load it.
license: MIT
metadata:
  version: 1.0.0
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

Run `printenv CLAUDE_CODE_REMOTE`. If it prints `true`, the session runs in a Claude Code cloud environment and the user cannot open the file. Still write the file, then send it to the user as a downloadable file with a tool that sends files to the user, such as `SendUserFile`. If no such tool is available, or sending fails, output the entire handoff document in chat as one fenced code block instead, so the user can copy it. Use a backtick fence of at least three backticks, and more than the longest backtick run in the document. In a cloud session, skip the path line described below.

In a local session, after you create or update a handoff file, end your output with one line that holds only the file's full absolute path as inline code, for example `/home/user/project/.handoffs/auth-migration.md`, so the user can copy it into the next session.
