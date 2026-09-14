# HTML output

Use the selected mode's outline. Render it as one self-contained HTML document
with inline CSS and JavaScript. Use a continuous page, section headings, and
a linked table of contents. Avoid top-level tabs. Make the layout readable
on a phone, and keep it usable without external assets or network access.

For a change walkthrough, present the five quiz questions as interactive
multiple-choice controls. After the reader selects an answer, show whether
it is correct and explain the reasoning. Keep feedback hidden until selection.

Use HTML and CSS for diagrams and native HTML lists for lists. Interactive
figures should expose a relationship through manipulation, such as coordinates
changing with position. Use static figures when they convey the same idea.

Preserve code whitespace with `<pre><code>` and an explicit `white-space: pre`
or `white-space: pre-wrap` rule. Escape source text for the HTML or JavaScript
context in which it appears. Provide keyboard-operable quiz controls and text
feedback so correctness does not depend on color alone.

Save to the user's specified location or the project's established ignored
artifact directory. If neither exists, use a temporary directory and disclose
that the file is temporary. Use a descriptive date-prefixed filename. Include
the comparison revisions when explaining a change, then return the absolute
file path as a clickable link.

## Verify

Open the file in a browser when available. Check navigation, narrow-screen
layout, code whitespace, and each quiz question's correct and incorrect
feedback. Exercise any interactive figures. Confirm that no external asset is
needed. If browser verification is unavailable, inspect the saved source and
report that rendering and interactions remain unverified.

Presentation adapted from Geoffrey Litt's
[HTML skill](https://gist.github.com/geoffreylitt/a29df1b5f9865506e8952488eac3d524#file-explain-diff-html-md).
