# Notion page

Use the outline the caller supplies to author a native Notion page. Headings,
paragraphs, lists, code blocks, tables, callouts, and quiz answers remain
native and editable. Do not embed a complete HTML rendering as the page body.

Read [notion-cli](../../notion-cli/SKILL.md) before interacting with Notion.
Use `ntn` for supported page and upload operations, then return the page URL.
Read the current endpoint documentation and schemas through the CLI before
constructing content. If a required feature needs the Notion connector, read
`notion://docs/enhanced-markdown-spec` through its resource reader or fetch
tool. Use the selected interface's documented syntax rather than treating
ordinary HTML tags as native Notion blocks.

Resolve the parent from the request or an established destination preference.
If there is no destination, ask where the page should live while preparing
the content. Fetch a named database's schema before creating a database item.
Do not replace an existing page unless the user requests an update.

## Quiz and figures

When the caller's outline includes a quiz, use native multiple-choice
questions. Put each answer's explanation inside a toggle so the reader can try
the question before revealing feedback. Keep the visible option text neutral;
show correctness inside the toggle. Follow the current specification for
toggle nesting.

Use native diagrams or static figures where sufficient. Embed HTML only for
a specific interactive figure or simulation whose controls reveal something
the static presentation cannot explain as clearly. Keep its introduction,
interpretation, and the rest of the explanation in native blocks.

For such a figure, create a self-contained HTML attachment through the
CLI or Notion connector upload tools, then embed the returned upload source
using that interface's documented syntax. Do not assume CLI upload IDs accept
the connector's embed syntax. An HTML code block displays source; it is not an
interactive embed. Do not load
[html-document.md](html-document.md) just to create one figure. Keep the
figure independent of external assets and verify its controls before
publishing it.

## Verify and deliver

Fetch the saved page. Verify the section order, native block structure, code
blocks, quiz toggle nesting, and any embedded figures. Check for unsupported
or missing content. When browser access is available, inspect the page and
exercise its interactive figures; fetching content alone does not prove that
an embed renders or runs correctly.

Return the page URL and any verification limitations. If Notion is unavailable
or publication fails, preserve the prepared content locally and report the
failure and path. Do not claim delivery or silently switch output formats.

Native page and quiz presentation adapted from Geoffrey Litt's
[Notion skill](https://gist.github.com/geoffreylitt/a29df1b5f9865506e8952488eac3d524#file-explain-diff-notion-md).
Selective interactive HTML figures follow the user's requested extension.
