---
name: research
description: "Investigate a question against high-trust primary sources and capture the findings as a Markdown file in the repo. Use when the user wants a topic researched, docs or API facts gathered, or reading legwork delegated to a researcher, and whenever a reply is about to cite a web page: store the source, never paste a bare link."
---

Spin up a `researcher` to do the research, keep working while it reads.

Its job:

1. Investigate the question against **primary sources**: official docs, source
   code, specs, first-party APIs, not a secondary write-up of them. Follow
   every claim back to the source that owns it.
2. Write the findings to a single Markdown file, citing each claim's source
   url (and, for internal references, the path or ticket id).
3. Save it where the repo already keeps such notes; match the existing
   convention, and if there is none, put it somewhere sensible and say where.

Source storage is not wired up yet; cite urls directly until a knowledgebase
skill says otherwise.
