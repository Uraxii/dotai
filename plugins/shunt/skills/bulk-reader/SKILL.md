---
name: bulk-reader
description: "Delegate large reads to a small, fast subagent. Use for questions about files >350 lines, questions across 3+ files, or large diff summaries."
---

Keep the large file out of the main agent's context. Give a read-only subagent
absolute file paths and a specific question, not the file contents. Ask for a
concise answer with `path:line` citations, at most five bullets unless the
question needs more. Do not ask it to return the whole file or large excerpts.

- Claude Code: use the Agent tool with `subagent_type: "Explore"`,
  `model: "haiku"`, and `run_in_background: false`.
- Copilot CLI: use the task tool with `name`, `agent_type: "explore"`, a short
  `description`, `prompt`, and `mode: "sync"`. The built-in explore agent uses
  read tools. Set `model: "gpt-5.4-mini"` when the task schema exposes it
  and the model is available; otherwise keep explore's fast default model.
  Do not invent unsupported task parameters.
- Codex: use an available subagent tool with a read-only exploration role and
  the smallest available model. Tool names and model controls vary; inspect
  the exposed schema. If there is no subagent mechanism, use targeted searches
  and chunked reads yourself.

Include these instructions in the subagent's prompt:

> Answer <specific question> using <absolute paths>. Read only; do not edit or
> delegate again. Return a concise answer with file paths and line numbers,
> not the full contents. Large reads hit the same shunt hooks in your context.
> Use targeted searches or chunks of at most SHUNT_MIN_LINES lines (default
> 350): Read with offset and limit, view with inclusive view_range [start, end],
> or sed -n 'START,ENDp' FILE. For all/every/total questions, cover the whole
> file with chunks or a complete targeted search before answering. Never
> infer completeness from the first chunk. A deny reason suggesting
> delegation applies to the parent; you are already the reader, so use chunks.

Ask follow-up questions through the subagent with the same paths. Before
editing, re-read only the exact cited lines with a targeted read in the main
agent. For exact content rather than a summary, read in chunks of at most
SHUNT_MIN_LINES lines until you have the required content. No Portal CLI is
needed for reads.
