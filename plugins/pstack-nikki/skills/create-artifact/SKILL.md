---
name: create-artifact
description: >-
  Use when content is already written and has to become a saved or published
  artifact rather than a chat reply. Settles whether it becomes a
  self-contained HTML file or a native Notion page, renders it, and verifies
  the result. A request to explain code, a diff, or a PR starts at the `how`
  skill instead, which calls this one to deliver its output.
---

# Create artifact

Render content the invoker already wrote. This skill does not explore a
codebase and does not write the explanation. The invoker owns the outline,
the section order, and every content rule. This skill owns the format.

## What the invoker supplies

- The content, as an outline with its sections already ordered.
- The format, if the user or the invoker has already settled one.
- The compared revisions, when the content explains a change.
- The destination: a save location for HTML, a parent page for Notion.

An input you cannot fill is an input to ask for or resolve below, never one
to invent.

## Settle the format first

Honor the format the user asked for, or an established preference for this
task. With no format stated, ask whether the user wants HTML or Notion, and
keep any independent work running while you wait for the answer. With no
channel to ask, which is the normal case for a spawned subagent, use HTML and
name that choice and its reason in the result.

Settle the format before you create a file or publish a page. The invoker may
settle it early and call back to render much later, so treat a format already
recorded for this task as settled and do not ask again.

## Read one format reference

Read only the reference for the selected format.

- **HTML.** One self-contained file the reader opens in a browser. Read
  [references/html-document.md](references/html-document.md).
- **Notion.** Native Notion blocks, with selective HTML where an interactive
  figure earns it. Read
  [references/notion-page.md](references/notion-page.md).

## Whoever invoked this skill writes and verifies

The invoker creates the file or the page, runs the selected reference's
verification, and returns the absolute file path or the page URL. An agent
with read-only access renders nothing: it returns its content to its own
invoker, saves no file, and publishes no page. Report any rendering or
publishing limitation with the result.
