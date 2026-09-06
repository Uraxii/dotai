# Critique the render

Produce pixels, hand them to someone who did not write the page, take back a
verdict. A critique that never opens an image is not one, and neither is one
the author writes about its own page.

Sections 1, 2 and 4 are yours. Section 3, the verdict table, is the critic's:
it lives in references/verdict.md, and you never fill or open it.

## 1. Produce pixels (author side)

Verified on this machine on 2026-09-06. Brave ships as a flatpak here. Its
sandbox reads and writes `/tmp` but not the repo, so both paths in the command
must be under `/tmp`.

```
cp page.html /tmp/dm-page.html
flatpak run com.brave.Browser --headless=new --disable-gpu --no-sandbox \
  --hide-scrollbars --window-size=1280,800 \
  --screenshot=/tmp/dm-desktop.png file:///tmp/dm-page.html
```

On success it prints `NNNNN bytes written to file /tmp/dm-desktop.png`. A
`Failed to write file` line means the target sits outside the sandbox, not
that rendering failed.

Take three captures by changing `--window-size` and `--screenshot`:

| Size | Filename | What it answers |
|---|---|---|
| 1280,800 | dm-desktop.png | the first frame a reader and a thumbnail get |
| measured | dm-full.png | the whole page, rhythm and repeated blocks |
| 390,844 | dm-mobile.png | wrapping, overflow, headline behaviour |

There is no full-page flag. The window is the viewport, so a page sized in
viewport units grows with it. At `--window-size=1280,3200` a
`min-height:100vh` hero is 3200px tall, fills the frame alone, and says
nothing about what it lost.

Build `dm-full.png` from a second copy. Freeze the viewport units at the 800px
desktop viewport, which makes 1vh 8px, then size the window to the height that
copy reports.

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
and the other three use `/tmp/dm-page.html` unchanged.

The `sed` misses `vmin`, `vmax`, and a height JavaScript sets. Section 3, in
references/verdict.md, catches those.

Take a fourth capture in the theme the page does not default to. Stamp
`data-theme` on a copy's root element: `dark` on a light-first page, `light`
on a dark-first one, where stamping `dark` changes nothing. A browser
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

The `0,/<html/` range edits only the first match, so the CSS selector
`:root[data-theme="light"]` further down survives. Rewrite that too and the
page renders byte-identical. `head -2` shows where the attribute landed.

Identical sums mean the stamp did not take and both captures show one theme.
Fix the stamp and recapture before writing a theme row. Two renders of one
unchanged file give one md5 here, so a difference is real. Webfonts are the
exception: a failed fetch shows fallback faces. Check that before answering
row 9 on the typeface.

Checked here, so nobody rechecks: the `Artifact` tool's read path returns HTML
rather than an image; the `claude-in-chrome` MCP tools were not connected; no
Chromium, Chrome or Firefox binary is on `PATH`. With no local browser, fall
back to the `agent-lab` skill, untested here.

## 2. Hand the captures to a fresh critic

You wrote the page, so you are its worst available reader. Asking the model
whose defaults produced this layout whether the layout is a tell asks an
author to mark its own paper. One study put language-model choice at roughly
13.6% of semantic-drift variance against 0.2% for the image model.

Spawn a fresh agent to fill in the verdict table in references/verdict.md.
Give it exactly this and nothing more:

- The four PNG paths from section 1, each labelled with its capture size.
- The path to references/verdict.md, for the tell list and the evidence rule.
- The code-facts block below, which you fill in first.

Withhold all of this:

- The HTML and the CSS, quoted, attached, or by path.
- The values you emitted, and the brief they came from.
- Your intent, your reasoning, anything you fixed in an earlier round.
- Any hint of the verdict you expect.

The critic reads each PNG with its file-reading tool. Reading HTML instead is
the substitution this step forbids. It returns the filled table and nothing
else.

Rows 5, 6 and 9 are part code question and the critic has no code. Hand these
over as facts, not judgments:

| Fact | Value |
|---|---|
| `h1` character count | |
| heading weight, then body weight | |
| font families, in declaration order | |

Guard the context window: four captures per round, the three sizes plus the
other-theme frame, landing in the critic's context, not yours.

## 4. Fix and recapture

Every `present` row gets a fix, and every `not-captured` row a recapture from
section 1 rather than a fix. Recapture, hand the new captures to a critic that
is fresh again, and stop after two rounds. The second critic is told nothing
about the first round, so it cannot ratify a fix it was shown. Anything still
present then ships with its row carried into the report.
