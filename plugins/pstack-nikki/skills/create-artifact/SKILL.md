---
name: create-artifact
description: >-
  Use when the user wants an explanation, report, walkthrough, or review
  delivered as a self-contained HTML file or a native Notion page instead of
  chat, and when a skill that already produced the content needs the output
  format settled, the artifact saved or published, and the result verified.
---

# Create artifact

Render content the caller already wrote. This skill does not explore a
codebase and does not write the explanation. The caller owns the outline,
the section order, and every content rule. This skill owns the format.

## Settle the format first

Honor the format the user asked for, or an established preference for this
task. With no format stated, ask whether the user wants HTML or Notion, and
keep any independent work running while you wait for the answer. Settle the
format before you create a file or publish a page.

## Read one format reference

Read only the reference for the selected format.

- **HTML.** One self-contained file the reader opens in a browser. Read
  [references/html-document.md](references/html-document.md).
- **Notion.** Native Notion blocks, with selective HTML where an interactive
  figure earns it. Read
  [references/notion-page.md](references/notion-page.md).

## The caller's coordinator writes and verifies

The coordinator creates the file or the page, runs the selected reference's
verification, and returns the absolute file path or the page URL. A
read-only exploring agent hands its content back to the coordinator instead.
It saves no file and publishes no page. Report any rendering or publishing
limitation with the result.
