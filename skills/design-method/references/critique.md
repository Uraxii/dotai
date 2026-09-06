# Critique the render

Produce pixels, hand them to someone who did not write the page, take back a
verdict. A critique that never opens an image is not one, and neither is a
critique the author writes about its own page.

## 1. Produce pixels (author side)

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
| measured | dm-full.png | the whole page, rhythm and repeated blocks |
| 390,844 | dm-mobile.png | wrapping, overflow, headline behaviour |

There is no full-page flag. The window is the viewport, so a page sized in
viewport units grows with it: at `--window-size=1280,3200` a
`min-height:100vh` hero is 3200px tall and fills the frame alone, and the
capture says nothing about what it lost.

Build `dm-full.png` from a second copy. Freeze the viewport units at the
800px desktop viewport, which makes 1vh 8px, then measure that copy and size
the window to the height it reports.

```
sed -E 's/([0-9.]+)[dsl]?vh/calc(\1 * 8px)/g' /tmp/dm-page.html \
  > /tmp/dm-tall.html
printf '%s' '<script>onload=()=>document.title=
"H="+document.documentElement.scrollHeight</script>' >> /tmp/dm-tall.html
flatpak run com.brave.Browser --headless=new --disable-gpu --no-sandbox \
  --window-size=1280,800 --virtual-time-budget=2000 --dump-dom \
  file:///tmp/dm-tall.html 2>/dev/null | grep -o 'H=[0-9]*' | head -1
```

It printed `H=1584` on a 100vh page, so `dm-full.png` is `/tmp/dm-tall.html`
at `--window-size=1280,1584`. No capture shows the title the probe rewrites,
and the other three use `/tmp/dm-page.html` unchanged, so the frozen units
decide nothing about the first frame or the phone.

The `sed` misses `vmin`, `vmax`, and a height JavaScript sets. Section 3
catches what it misses.

Take a fourth capture in the theme the page does not default to. Stamp
`data-theme` on the root element of a copy: `dark` on a light-first page,
`light` on a dark-first one, where stamping `dark` changes nothing. A browser
dark-mode flag does not stand in for `prefers-color-scheme`.

```
sed '0,/<html/s/<html/<html data-theme="light"/' /tmp/dm-page.html \
  > /tmp/dm-other.html
head -2 /tmp/dm-other.html
flatpak run com.brave.Browser --headless=new --disable-gpu --no-sandbox \
  --hide-scrollbars --window-size=1280,800 \
  --screenshot=/tmp/dm-other.png file:///tmp/dm-other.html
md5sum /tmp/dm-desktop.png /tmp/dm-other.png
```

The `0,/<html/` range confines the edit to the first match, so the CSS
selector `:root[data-theme="light"]` further down survives. Rewrite that too
and the page renders byte-identical. `head -2` shows where the attribute
landed.

Read the two sums. Identical sums mean the stamp did not take and both
captures show one theme, so fix the stamp and recapture before writing a theme
row. Two renders of one unchanged file give one md5 here, so a difference is
real. Webfonts are the exception: the fetch can fail, so a capture may show
fallback faces. Check that before answering row 9 on the typeface.

Checked here so nobody rechecks them: the `Artifact` tool's read path returns
HTML rather than an image; the `claude-in-chrome` MCP tools were not
connected; no Chromium, Chrome or Firefox binary is on `PATH`. On a machine
with no local browser the fallback is the `agent-lab` skill, untested here.

## 2. Hand the captures to a fresh critic

You wrote the page, so you are the worst available reader of it. The model
that picked this layout is the one whose defaults produced it, so asking it
whether the layout is a tell asks an author to mark its own paper. One study
put language-model choice at roughly 13.6% of semantic-drift variance against
0.2% for the image model.

Spawn a fresh agent to fill in the table in section 3. Give it exactly this and
nothing more:

- The four PNG paths from section 1, each labelled with its capture size.
- The path to this file, for the tell list and the evidence rule.
- The code-facts block below, which you fill in first.

Withhold all of this:

- The HTML and the CSS, quoted, attached, or by path.
- The values emitted in steps 1 to 7, and the brief they came from.
- Your intent, your reasoning, anything you fixed in an earlier round.
- Any hint of the verdict you expect.

The critic reads each PNG with its file-reading tool, so the image enters its
context; reading HTML instead is the substitution this step forbids. It returns
the filled table and nothing else.

Rows 5, 6 and 9 are part code question and the critic has no code. Measure
these and hand them over as facts, not judgments:

| Fact | Value |
|---|---|
| `h1` character count | |
| heading weight, then body weight | |
| font families, in declaration order | |

Guard the context window: four captures per round, the three sizes plus the
other-theme frame. They land in the critic's context, not in yours.

## 3. The verdict, written by the critic (critic side)

Run this before filling a single row, every round. It answers whether the tall
capture holds anything the first frame does not, using only the two PNGs.

```
magick compare -metric RMSE \
  \( /tmp/dm-full.png -resize 64x64! -colorspace Gray \) \
  \( /tmp/dm-desktop.png -resize 64x64! -colorspace Gray \) null:
```

Read the bracketed number it prints. At 0.20 or more the tall capture carries
page the first frame does not. Under 0.20 the two are near-identical, so the
tall capture is one screen stretched and the rest of the page is missing from
it. Measured here: 0.107 for a `min-height:100vh` page at 1280,3200, against
0.399 for that same page captured by section 1.

Under 0.20, stop. Write `not-captured`, never `absent`, in every row you cannot
decide from the 1280x800 and 390x844 frames, rows 1, 3, 4, 7 and 8 at minimum,
and put the number in the evidence cell. `not-captured` is not a pass: it sends
the page back to section 1 for a recapture.

One row per tell. Verdict is `present`, `absent`, or `not-captured`. Evidence
names what in the image decided it, or the code fact from section 2 where the
tell is not a visible one. An empty evidence cell voids the row.

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
budget the author spends while writing the CSS, and no one reads 3% off an
image. Answer it on whether the accent highlights or floods, and say what you
looked at.

Row 12 is open on purpose and carries the same evidence discipline. Name the
element, say where it is, say what is wrong with it. A fixed list that returns
all-absent on a page with a visibly stretched chip is self-scoring wearing a
checklist. If nothing is wrong, write `absent` and say what you checked.

Rows 5, 6 and 9 lean on the code-facts block from section 2. Say for each
whether the image or that block decided it. Rows 2, 3, 8, 9 and 11 restate
prohibitions `artifact-design` carries; what they add is a place to write the
verdict and the evidence down.

Never judge your own page, by a number or by a word. This table is not the
author's to fill; section 2 says who fills it. One pack's 58 gates run over
that pack's own `site/examples/` returned 61 hard failures across 11 of its 18
example pages, every one stamping `gates: all-pass` in its own CSS. A fresh
agent in the same model family is weaker than a human or a different model;
references/evidence.md scores how much weaker.

## 4. Fix and recapture

Every `present` row gets a fix. Recapture, hand the new captures to a critic
that is fresh again, and stop after two rounds. The second critic is told
nothing about the first round either, so it cannot ratify a fix it was shown.
Anything still present at that point ships with the row carried into the
report, so the reader knows what was seen and left.
