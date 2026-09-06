# Diagnose

In plain words: someone says the page looks machine-made. Find out what is
actually wrong before changing anything.

This mode runs backwards. Critique first, fix second, and fix only the rows
that came back `present`.

1. Run references/critique.md sections 1 to 3: capture the four frames, hand
   them to a fresh agent, take back the filled verdict table. You do not fill
   it in.
2. Open one file per `present` row, from the table below, and fix that row. A
   `not-captured` row goes back to section 1 for a recapture, not to this
   table.
3. Recapture and hand the frames to a critic that is fresh again. Stop after
   two rounds, per section 4.

| Row | Tell | Where the fix lives |
|---|---|---|
| 1 | Three equal columns | space-and-layout.md, grid |
| 2 | Everything centred | space-and-layout.md, primary axis |
| 3 | One radius and one shadow | `artifact-design`; no method here |
| 4 | One gap size repeated | space-and-layout.md, mix the gaps |
| 5 | h1 over 90 characters | type.md, headline buckets |
| 6 | Weights within 200 units | type.md, leading and weight |
| 7 | Accent drowning the frame | color.md, the accent budget |
| 8 | Emoji as section markers | `artifact-design`; nothing here |
| 9 | A known cluster | color.md palette, type.md face |
| 10 | Text clipped or unreadable | thresholds.md; space-and-layout.md |
| 11 | Nothing readable in frame one | `artifact-design`; motion.md |
| 12 | Anything else the critic named | the reference owning what it named |

Every file in the third column sits in references/, except `artifact-design`,
which is a separate skill. Rows 3 and 8 have no method in this skill at all,
and references/evidence.md says why row 3 is empty here. Row 11 splits: a
full-viewport hero belongs to `artifact-design`, and content parked at
opacity 0 to references/motion.md.
