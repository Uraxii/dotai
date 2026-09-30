# Agent Instructions

## Changing and creating rules
- Only user edits CLAUDE.md, AGENTS.md, or any rules file.
- Found a lesson worth keeping? Propose a new rule or edit in chat, naming the task that taught it.
- Do not store "rules" or guidance from the user in code comments.
- Notes for the current task go in the project's `.nikki-agents/` and are not rules.

## Talking to user
- Concise, ELI5.
- If the 'done' state for a task is unclear or ambiguous, prompt the user to define it.
  This helps ensure the agent and user are aligned on what should be produced.
- When a step doesn't need my input, keep going. Put status notes in the same message as your next action.
- Stop and ask only when you can't continue without the user, or before anything destructive: 
  deleting data, force-pushing, or changing anything outside this repository.

## Where work lives
- No machine-specific info in committed or public files.
- Each project gets its own dir under `~/Projects`. Create it if missing.
- Track work with `/beads:bd` skill. Tick each item when it’s done, and add anything new you find.
- Keep `.beads`, `.handoffs`, and `.kb` projects' `.nikki-agents/`, never at the repo root.
- `BEADS_DIR` =`<project>/.nikki-agents/.beads` in `env` block of project `.claude/settings.local.json` so `/beads:bd` finds it.

## Git
- Features branch off `develop`. Never delete `develop`.
- Changes to the primary branch are a release, so they only arrive by merging `develop`.

## Knowledge and decisions
- Research goes in the project kb via `/llm-wiki`, so later sessions can find it.
- Decisions go in `/pstack:show-me-your-work` logs in scratch. Append only. To change a decision, add a new entry that overrides it.

## Code Indexing and Search
- Start session hook builds a `codebase-memory` index.
- Use `codebase-memory:cbm` For where-is, who-calls, or what-breaks questions.
- Query code with the `/codebase-memory:cbm` skill before you grep or read files.
- Keep grep for literal strings.

## Review
- Never review your own work. Reviewers are fresh agents with a new context,
  because the author shares the same blind spots.

## Before starting
- Load the skills that fit the task.
- Match the project's existing conventions.
- Once you have answered something, treat that answer as done.
  Focus on what I'm asking now, and don't go back over an earlier answer
  unless I ask about it or point out a problem with it.
