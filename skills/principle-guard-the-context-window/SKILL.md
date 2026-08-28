---
name: principle-guard-the-context-window
description: Use when a step is about to pull bulk into the conversation, such as dumping a long log or stack trace, reading many files to answer one question, capturing screenshots or rendered frames, pasting a big JSON graph or plan output, or fanning work out across phases. Routes bulk to subagents and keeps only summaries in the main thread.
---

# Guard context window

Context finite and non-renewable within session. Every token entering must earn
its place. Overflow degrade reasoning, create compression artifact, halt
progress. Unlike compute or wall time, context spent cannot be reclaimed.

## Pattern

- **Isolate bulk.** Route verbose output, screenshots, large documents to
  subagent. Main thread get summary, not raw payload.
- **Do not read what you will not use.** Select by relevance. File not needed
  for this task -> skip it.
- **Keep hot content inline.** Template or reference used every invocation
  belong in skill file, not separate file costing a read each time.
- **Size phases, cap scope.** Files per phase, turn budget, account mechanism
  cost.
- **Query, do not dump.** Grep the error out of the log, tail the failures out
  of the test run, read the field out of the JSON, list matching files before
  reading any.
- **Screenshots never decay.** They cost every later turn. Capture fewest, at
  modest width, only to judge APPEARANCE. Value check goes through text digest.

Rule of thumb: raw payload over ~100 lines and not needed verbatim ->
summarise or delegate.
