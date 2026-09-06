# Critique the render

Produce pixels, load the pixels, write a verdict. A critique that never opens
an image is not a critique, and a pack that claims one while never instructing
the agent to look is the failure this file exists to avoid.

## 1. Produce pixels

Verified on this machine on 2026-09-06. Brave ships as a flatpak here, and its
sandbox can read and write `/tmp` but not the repo, so copy the page to `/tmp`
first. Both paths in the command must be under `/tmp`.

```
cp page.html /tmp/dm-page.html
flatpak run com.brave.Browser --headless=new --disable-gpu --no-sandbox \
  --hide-scrollbars --window-size=1280,800 \
  --screenshot=/tmp/dm-desktop.png file:///tmp/dm-page.html
```

It prints `NNNNN bytes written to file /tmp/dm-desktop.png` on success. A
`Failed to write file` line means the target sits outside the sandbox, not that
rendering failed.

Take three captures by changing `--window-size` and `--screenshot`:

| Size | Filename | What it answers |
|---|---|---|
| 1280,800 | dm-desktop.png | the first frame a reader and a thumbnail get |
| 1280,3200 | dm-full.png | the whole page, rhythm and repeated blocks |
| 390,844 | dm-mobile.png | wrapping, overflow, headline behaviour |

The capture is the window, so a taller window is how you see more of the page.
There is no full-page flag.

Take a fourth capture in the theme the page does not default to. Stamp
`data-theme` on the root element of a copy. A light-first page is stamped
`dark`; a dark-first page is stamped `light`, and stamping `dark` on it changes
nothing. Do not trust a browser dark-mode flag to stand in for
`prefers-color-scheme`.

```
sed '0,/<html/s/<html/<html data-theme="light"/' /tmp/dm-page.html \
  > /tmp/dm-other.html
head -2 /tmp/dm-other.html
flatpak run com.brave.Browser --headless=new --disable-gpu --no-sandbox \
  --hide-scrollbars --window-size=1280,800 \
  --screenshot=/tmp/dm-other.png file:///tmp/dm-other.html
md5sum /tmp/dm-desktop.png /tmp/dm-other.png
```

The `0,/<html/` range confines the edit to the first match, so the CSS selector
`:root[data-theme="light"]` further down the file is left alone. A plain
`sed s/data-theme="light"/.../` rewrites that selector too and renders a
byte-identical page. `head -2` shows the attribute landed on the `<html>` tag.

Read the two sums. Identical sums mean the stamp did not take and both captures
show one theme. Identical file sizes alone are the trap: that is exactly how
this failed before it was caught. Fix the stamp and recapture before writing a
single theme row.

Two renders of one unchanged file give one md5 here, so a difference is real.
Webfonts are the exception: the fetch can fail, so a capture may show fallback
faces. Check that before answering row 9 on the typeface.

Checked here so nobody rechecks them: the `Artifact` tool's read path returns
HTML rather than an image and cannot serve as the critique; the
`claude-in-chrome` MCP tools were not connected; no Chromium, Chrome or Firefox
binary is on `PATH`, so the flatpak is the browser. On a machine with no local
browser the fallback is the `agent-lab` skill, untested here.

## 2. Load the pixels

Read each PNG with the file-reading tool so the image itself enters context.
Reading the HTML again instead is the exact substitution this step forbids.

Guard the context window: four captures per round is the budget, which is the
three sizes above plus the other-theme frame. A long page gets one tall
capture, not eight scrolled ones.

## 3. Write the verdict

One row per tell. Verdict is `present` or `absent`. Evidence names what in the
image decided it, or the CSS line where the tell is a code fact rather than a
visible one. An empty evidence cell voids the row.

| # | Tell | Verdict | Evidence |
|---|---|---|---|
| 1 | Three equal columns, each icon over heading over two lines | | |
| 2 | Everything centred, no primary axis | | |
| 3 | One radius and one shadow stamped on every block | | |
| 4 | One gap size repeated across the whole page | | |
| 5 | h1 over 90 characters at display size | | |
| 6 | Heading and body weight within 200 units | | |
| 7 | Accent drowning the frame: it fills a background panel, a full-width bar, or many marks at once, rather than picking out a few | | |
| 8 | Emoji standing in as section markers | | |
| 9 | One of the known clusters: cream and serif and terracotta; a near-black ground whose only colour is one or two high-chroma marks; purple-to-blue gradient hero; Inter or Space Grotesk as the safe face | | |
| 10 | Text clipped, overlapping, or unreadable in either theme | | |
| 11 | Nothing readable in the first frame: a full-viewport hero, or content parked at opacity 0 | | |
| 12 | Anything else in the frame you can see and do not like | | |

Row 7 is a judgment, not a measurement. The 3% figure in SKILL.md step 4 is a
budget for writing the CSS; nobody can read 3% off an image, so answer row 7 on
whether the accent is highlighting or flooding and say what you looked at.

Row 12 is open on purpose and carries the same evidence discipline as the
others. Name the element, say where it is, say what is wrong with it. A fixed
list that returns all-absent on a page with a visibly stretched chip is
self-scoring wearing a checklist. If nothing is wrong, write `absent` and say
what you checked.

Rows 5, 6 and 9 are partly answered from your own CSS. Answer them anyway, and
say which source you used.

Rows 2, 3, 8, 9 and 11 restate prohibitions `artifact-design` already carries.
They add no new rule. What they add is a place to write the verdict and the
evidence down, which prose cannot hold.

Never write a numeric self-score. A page scored by the model that wrote it
reports a pass it did not earn. One pack's 58 gates were run over that pack's
own `site/examples/` and returned 61 hard failures across 11 of its 18 example
pages, every one of which stamped `gates: all-pass` in its own CSS.

## 4. Fix and recapture

Every `present` row gets a fix. Recapture, rewrite the table, and stop after
two rounds. Anything still present at that point ships with the row carried
into the report, so the reader knows what was seen and left.
