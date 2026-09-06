# What this rests on

Read this before quoting any number in this skill as established fact.

## Sources and licences

| Pack | Licence | What was taken |
|---|---|---|
| Nutlope/hallmark | MIT | type ratios and caps, headline buckets, tracking, OKLCH palette layers, accent budget, the eight states, dark derivation, spacing ladder, grid and z-index, duration bands, easing set |
| Cuuper22/anti-slop-design | MIT | fluid ladders, twelve-step ramp and role map, token tiers, dark derivation, density table, motion tokens |
| Owl-Listener/designer-skills | MIT | duration and easing tables, choreography, density as an operator |
| anthropics/skills | Apache-2.0 | nothing; no method carried, so the notice obligation does not bite |

Both MIT packs give a dark derivation, and where both speak they agree. They do
not both speak everywhere. Two of the six operations are hallmark's alone:
anti-slop-design is silent on reducing body weight by 50 units, and does not
state holding hue unchanged as a rule. The numbers this skill carries, paper 12
to 18%, ink 92 to 96%, chroma down 0.02 to 0.04, lightness up 5 to 10%, body
weight down 50 units and hue unchanged, are hallmark's column throughout.

Neither pack derives a dark form of the twelve-step ramp. Radix does, and
references/color.md now reconciles our values against it; the walk is a
selection, not an invention.

All three MIT packs are credited by name. Methods and numbers are not
copyrightable; the expression is. No pack's prose is reproduced here. Several
phrasings do come from our own extraction spec at
`.nikki-agents/research/design-skills-eval/30-extraction-spec.md`, which is our
researcher's writing rather than a pack's: "hand-picked list wearing the word
ratio", "curated ladder on a 4px grid, not a generated one", "bounded set of
moves" and "reads as drama rather than weight".

## Claims whose evidence is weak

- **All of it, first because it bears on all of it.** No pack published a
  controlled comparison showing its method improves output. The case for these
  numbers is that they are specific and internally consistent. Nobody measured
  them.
- **The measure figure.** One pack attributes the 45 to 75 character band to
  typographic research going back to the 1920s and names no study. The number
  is widely used, so keep it and drop the provenance claim.
- **The four-level hierarchy taxonomy.** Primary, secondary, tertiary,
  quaternary is vocabulary, not procedure: the source gives no rule for
  assigning a level and no mapping from level to a size, weight or spacing
  value. Its verification move is a squint test, which an agent cannot run.
  Not carried into this skill.
- **The spring curve.** Two packs, opposite verdicts on the same
  `cubic-bezier`, both self-attested. See the ruling in references/motion.md.
- **The ramp role map contradicts the ramp.** The source states the twelve-step
  role map with lightness columns of 0.97 to 0.83, 0.78 to 0.71, 0.64 to 0.44
  and 0.43 to 0.22, and prints the worked ramp beside it reading 0.99 to 0.86,
  0.80 to 0.73, 0.64 to 0.49 and 0.43 to 0.25. Both cannot be right.
  references/color.md follows the worked ramp, because that is the artefact you
  paste, and says so at the table.
- **A pack contradicting its own tokens.** One pack's typography file names
  Inter as the single most common AI tell while its own fintech token file
  sets `--font-body` to Inter. Do not assume a pack's shipped tokens obey its
  own prohibitions, and do not assume ours do either without checking.
- **The shadow ramp progression.** The pattern of quadrupling blur and offset
  with alpha rising 0.02 to 0.04 per step is one researcher's reading of three
  token values, not a rule any source wrote down.
- **The hue mapping for a mood, now verified.** It reached this skill
  second-hand. Fetched at source on 2026-09-06 and checked: all five bands
  match. Capture at `design-skills-eval/sources/hallmark-ref-custom-theme.md`,
  section B.1. The fetch recovered one number the second-hand copy lost: a hue
  derived from a mood clamps chroma to 0.12 to 0.16, not the 0.12 to 0.20 that
  applies to a named anchor. The source gives no fallback at all for a mood it
  does not recognise, which is why step 4's job table is labelled ours.
- **Our own verification loop.** The correction that cut hallmark's
  verification score from 4 to 2 held that a self-attested gate with a
  demonstrated false-pass rate is nearer to no verification than to
  verification. That standard lands this skill's critique step near 3 of 5, not
  5: the tell list is specific and the evidence cell is enforced, but every
  capture and every fix is still the author's, and a fresh critic in the
  author's own model family is a weaker guarantee than a human reader or a
  different model. It lifts the step above a self-score. It is not an outside
  check.

## Evidence that runs against the method

Above is about the numbers. This is about whether following a method like this
one changes the output at all. The corpus answers that question worst.

- **Practitioners on the source pack's own example pages.** "The rest are all
  practically identical and are the go-to output for what you get if you ask
  Sonnet to build a website." Asked whether anyone had got it to work: "For me
  it still pretty much looks like slop." A third, across several such skills:
  "the design itself is the same unless you are extremely explicit." Two of the
  nine comments were favourable. `16-hallmark-reception.md`, B11 and 5.2.
- **The same pack's pages against its own gates.** 61 hard failures across 11
  of its 18 example pages, every one stamping `gates: all-pass` in its own CSS.
  Our correction C2 used that to cut the gate score and let the method score
  stand, because the method was read directly. That has a hole: reading a
  method confirms it exists and is self-consistent, not that it works. Those 18
  pages are the closest thing to an output test in this corpus, and the verdict
  on them is negative to mixed.
- **Two sources arguing no rule set fixes this.** One rules out a cleverer
  prompt, a prose mega-spec written up front, and a coding agent working alone.
  The other holds that slop is not a bug you prompt your way out of, and that
  the missing ingredient is a human pause rather than a better rule set.
  Judgments, not measurements: `11-slop-taxonomy.md` F27 and F28. This skill is
  a rule set with a critique bolted on, so both are aimed at it. Step 8's fresh
  critic is the nearest thing here to that pause, and a machine is not a human.

## Areas with no method, deliberately left empty

- **Border radius.** No pack derives a radius scale. One ships a fixed set per
  domain, for example 6px, 8px, 12px and a 9999px pill, with no reason given
  and no rule for deriving a nested radius from an outer one, which is the
  question that actually comes up.
- **Icon sizing.** No pack carries a size scale, an optical size rule, or a
  stroke weight tied to a size. The nearest figure is an accessibility example
  about tap targets, which is not an icon-size method.
- **Light-mode shadow derivation.** No pack produces a shadow from a base
  colour and an elevation level. What exists is a short allow-list: a whisper,
  `0 1px 2px oklch(20% 0.01 H / 0.05)`, and a hairline alternative to a 1px
  border, `0 0 0 1px oklch(30% 0.01 H / 0.06)`. Never stack shadows, never put
  a coloured glow on a light ground, and remember a drop shadow on a dark card
  renders as a glow. Depth on dark comes from lightness, not shadow.

Nothing has been invented to fill these three. Treat them as judgment calls.

## Audit of `artifact-design` for the three unaudited areas

Checked against the resident skill on 2026-09-06. It covers elevation and
radius qualitatively, spend-by-role and a ban on `rounded-lg` everywhere, with
no value, ramp or nesting rule, and does not cover icon sizing at all. So the
shadow allow-list above is genuinely new and the other two gaps are real on
both sides.
