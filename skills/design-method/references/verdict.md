# 3. The verdict, written by the critic (critic side)

In plain words: you are a fresh agent holding four screenshots of a page you
did not write. Fill in the table below from them. This is the only file you get.

Run this before filling a single row, every round. It answers whether the tall
capture holds anything the first frame does not, from the two PNGs alone.

```
magick compare -metric RMSE \
  \( /tmp/dm-full.png -resize 64x64! -colorspace Gray \) \
  \( /tmp/dm-desktop.png -resize 64x64! -colorspace Gray \) null:
```

Read the bracketed number. At 0.20 or more the tall capture carries page the
first frame does not. Under 0.20 the two are near-identical: the tall capture
is one screen stretched, and the rest of the page is missing from it. Measured
here: 0.107 for a `min-height:100vh` page at 1280,3200, against 0.399 for that
same page captured by section 1 of references/critique.md.

Under 0.20, stop. Write `not-captured`, never `absent`, in every row you cannot
decide from the 1280x800 and 390x844 frames, rows 1, 3, 4, 7 and 8 at minimum.
Put the number in the evidence cell. `not-captured` is not a pass: it sends the
page back to section 1 of references/critique.md for a recapture.

One row per tell. Verdict is `present`, `absent`, or `not-captured`. Evidence
names what in the image decided it, or the code fact you were handed where the
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

Row 7 is a judgment, not a measurement. The 3% figure in references/color.md is
a budget the author spends in the CSS, and no one reads 3% off an image. Answer
on whether the accent highlights or floods, and say what you looked at.

Row 12 is open on purpose and carries the same evidence discipline. Name the
element, where it is, and what is wrong with it. A fixed list that returns
all-absent on a page with a visibly stretched chip is self-scoring wearing a
checklist. If nothing is wrong, write `absent` and say what you checked.

Rows 5, 6 and 9 lean on the code-facts block you were handed. Say for each
whether the image or that block decided it. Rows 2, 3, 8, 9 and 11 restate
prohibitions `artifact-design` carries, and add a place to write the verdict
and the evidence down.

Never judge your own page, by a number or by a word. Filling this table is
yours; the author never fills a row of it. One pack's 58 gates run over that
pack's own `site/examples/` returned 61 hard failures across 11 of its 18
example pages, every one stamping `gates: all-pass` in its own CSS. A fresh
agent in the same model family is weaker than a human or a different model.
references/evidence.md scores how much weaker.
