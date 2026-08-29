---
name: reflect
description: "Mines the active session transcript with three parallel reviewer agents, synthesizes the durable learnings, and routes each one to a concrete edit on an existing skill. Use when the user says reflect, after a complex task lands cleanly, after dead ends resolve into a path that generalizes, or after the user corrects the agent's approach mid-task."
---

# Reflect

Mine the conversation for durable learnings, then route each into a skill edit.

## When to invoke

- The user said "reflect".
- A complex task (5+ tool calls) landed clean and the recipe is worth keeping.
- Dead ends were hit, the working path was found, and it generalizes.
- The user corrected the approach mid-task.
- A non-trivial workflow emerged that no skill captures.

Skip a trivial or off-topic conversation. Skip one already covered by a skill
the parent followed correctly. One-offs are not learnings.

## 1. Locate the active transcript

Find the transcript before fanning out. Search the active workspace's
transcript directory only. Globbing across other workspaces reads private
chats from unrelated projects.

```bash
ls -t <transcripts>/*.jsonl <transcripts>/*/*.jsonl \
  <transcripts>/*/subagents/*.jsonl 2>/dev/null | head -10
```

Layouts: flat (`<id>.jsonl`), nested (`<id>/<id>.jsonl`), and subagent
(`<parent>/subagents/<child>.jsonl`).

Read the first JSONL line of each candidate and check that its opening user
message is this conversation's first prompt. Take the match. If nothing
resolves, write a tight digest of the session and pass that instead.

## 2. Spawn three reviewers in parallel

One message, three `reviewer` agents, each carrying the full spawn brief.
Model per call from the `poteto-mode` skill's `models.md` (`judgment and
prose` row); row absent -> omit `model`. Keep their context-lookup tools.
FORBIDDEN: no writes, no commits, inspection only. The parent applies edits.

- Judgment lens: `references/judgment-reviewer.md`
- Tooling lens: `references/tooling-reviewer.md`
- Divergent lens: `references/divergent-reviewer.md`

Pass each template verbatim, substituting path or digest where marked.

## 3. Synthesize

One more `reviewer`, same model row, lookup tools intact: its quality check
spot-verifies citations. Use `references/synthesizer.md` verbatim with each
reviewer's full output inlined where marked. It returns an Accepted, Rejected,
and Backlog list.

Then move any Accepted item that a lint rule, script, metadata flag, or
runtime check would enforce more reliably to Backlog
(`principle-encode-lessons-in-structure`). Last pass before edits land.

## 4. Apply

Present the whole Accepted, Rejected, and Backlog output and wait for explicit
approval. The user picks the subset to apply and may redirect routings. Skill
edits change every future agent, so never auto-apply.

File Backlog items to the project's issue tracker without asking. Those are
tracker submissions, not skill edits. Only Accepted waits.

For each approved item, follow its Routing exactly. Run any SKILL.md validator
the project ships over every touched skill.

- Trivial edit (one bullet, a tightened sentence, a stale fact): the parent
  does it directly.
- Substantive edit (a new section, a new table, more than about 10 lines),
  `tune description: <skill path>`, or `new skill: <kebab-name>`: hand to a
  `developer` following the Authoring a skill role
  (`roles/authoring-a-skill.md` in the `poteto-mode` skill). Do not invent the
  shape ad hoc.

## 5. Summarize

Short list, no preamble:

- Edits applied: `<skill path>`, one line each.
- New skills: `<skill path>`, one line each.
- Backlog filed: `<issue title>`, one line each.
- Dropped: one line per rejected finding, plus the synthesizer's reason.
