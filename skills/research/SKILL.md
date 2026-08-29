---
name: research
description: Investigate a question against high-trust primary sources, store every web source cited into the project knowledgebase, and capture the findings as a Markdown file in the repo. Use when the user wants a topic researched, docs or API facts gathered, reading legwork delegated to a researcher, or whenever a web page is about to be cited, referenced, or kept.
---

Spin up a `researcher` to do the research, keep working while it reads.

Its job:

1. Investigate the question against **primary sources**: official docs, source
   code, specs, first-party APIs, not a secondary write-up of them. Follow
   every claim back to the source that owns it.
2. Store each web source it relies on (below). A cited link rots and carries
   no content.
3. Write the findings to a single Markdown file, citing each claim's stored
   note (and the url in that note's `## Refs`).
4. Save it where the repo already keeps such notes; match the existing
   convention, and if there is none, put it somewhere sensible and say where.

## Storing a web source

Deterministic, zero model spend: the workbench fetches and parses the page.
Do not read or summarize it into the note.

```bash
agent-workbench kb clip "<url>" --project <project>
agent-workbench kb query "<terms>" --project <project> --type source
```

`<project>` is the repo or workstream name. `clip` writes a `type: source`
note with title, author, site, published, fetched, description, tags, the
cleaned body, and the url under `## Refs`, then atomizes and reindexes.

Rules:

- Never paste a bare link in a report or the knowledgebase when the content
  matters. Clip it, then cite the stored note.
- Internal or code references stay cited (path or ticket id), not clipped.
- `question` and `summary` stay empty on capture; a later classifier fills
  them.
- JS-heavy or auth-gated pages may not extract. Note that and cite the url
  under `## Refs` when the body comes back empty.

Verbs and flags: the `agent-workbench` skill, `modes/kb.md`.
