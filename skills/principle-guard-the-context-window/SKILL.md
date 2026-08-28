---
name: principle-guard-the-context-window
description: Use when a step is about to pull bulk into the conversation, such as dumping a long log or stack trace, reading many files to answer one question, capturing screenshots or rendered frames, pasting a big JSON graph or plan output, or fanning work out across phases. Routes bulk to subagents and keeps only summaries in the main thread.
---

# Guard context window

Context finite and non-renewable within session. Every token entering must
earn its place.

**Why:** overflow degrade reasoning, create compression artifact, halt
progress. Unlike compute or wall time, context spent inside session cannot be
reclaimed.

## Pattern

- **Isolate bulk.** Route verbose output, screenshots, large documents to
  subagent. Main thread get summary, not raw payload.
- **Do not read what you will not use.** Select by relevance. File not needed
  for this task -> skip it.
- **Keep hot content inline.** Template or reference used every invocation
  belong in skill file, not separate file costing a read each time.
- **Size phases, cap scope.** Files per phase, turn budget, account mechanism
  cost.

## Bulk sources and cheaper substitutes

- Engine/editor logs, stack traces -> grep for error, paste matched lines.
- Screenshots and rendered frames -> they never decay, cost every later turn.
  Capture fewest, modest width, only to judge APPEARANCE. Value check goes
  through text state digest.
- Generated JSON (workflow graph, scene dump, infra plan) -> query the field,
  not the whole document.
- Repo-wide search -> list matching files first, read the few that matter.
- Test or CI output -> tail failures, not full run.
- Binary/asset inspection -> report shape and counts, not contents.

Rule of thumb: raw payload over ~100 lines and not needed verbatim ->
summarise or delegate.
