# What this rests on

Read this before quoting any number in this skill as established fact.

## Sources and licences

| Pack | Licence | What was taken |
|---|---|---|
| Nutlope/hallmark | MIT | type ratios and caps, headline buckets, tracking, OKLCH palette layers, accent budget, the eight states, dark derivation, spacing ladder, grid and z-index, duration bands, easing set |
| Cuuper22/anti-slop-design | MIT | fluid ladders, twelve-step ramp and role map, token tiers, dark derivation, density table, motion tokens |
| Owl-Listener/designer-skills | MIT | duration and easing tables, choreography, density as an operator |
| anthropics/skills | Apache-2.0 | nothing; no method carried, so the notice obligation does not bite |

Both MIT packs give the dark derivation and they agree on every operation. The
numbers this skill carries, paper 12 to 18%, ink 92 to 96%, chroma down 0.02 to
0.04, lightness up 5 to 10%, body weight down 50 units and hue unchanged, are
hallmark's column. Neither pack derives a dark form of the twelve-step ramp;
that walk is ours and references/color.md labels it.

All three MIT packs are credited by name. Methods and numbers are not
copyrightable; the expression is. No pack's prose is reproduced here. Several
phrasings do come from our own extraction spec at
`.nikki-agents/research/design-skills-eval/30-extraction-spec.md`, which is our
researcher's writing rather than a pack's: "hand-picked list wearing the word
ratio", "curated ladder on a 4px grid, not a generated one", "bounded set of
moves" and "reads as drama rather than weight".

## Claims whose evidence is weak

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
- **The hue mapping for a mood.** The mood-to-hue table in SKILL.md step 4
  comes from a second-hand capture of a source file, not from the file itself.
  Verify against the pack before treating it as exact.
- **All of it.** No pack published a controlled comparison showing its method
  improves output. The case for these numbers is that they are specific and
  internally consistent.

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
