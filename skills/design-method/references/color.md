# Colour

Work in OKLCH. One lightness number means the same apparent brightness across
hues, and hue holds as you lighten. HSL does neither.

## Anchor hue H

A colour named in the brief, a brand hex included, converts to OKLCH. Its hue
is H, chroma clamped to 0.12 to 0.20.

No colour named: read H off the mood word, chroma tighter at 0.12 to 0.16.
Warm 30 to 60, technical or industrial 220 to 250, botanical 130 to 160, late
night or neon 280 to 320, sun-drenched or market 60 to 80 amber. Verified at
source.

No mood word, or one off that list: the job row from references/type.md sets H.
There is no default hue, because a default hue is how every page comes out
blue.

| Job row | H |
|---|---|
| dashboard, admin, analytics, monitoring, developer tool | 235 |
| app, tool, SaaS, fintech, e-commerce | 145 |
| landing page, portfolio, editorial, healthcare, luxury | 45 |
| report, review, postmortem, status page | 70 |
| none | name one outside 200 to 280, and the brief line it came from |

The bands are the source's; assigning a job to one is ours, and the spread is
the point. Two more fallbacks, ours: a word naming a light level, such as dark
or night, sets the default theme and never the hue; two hue words, take the
first.

## The four layers

Emit four layers at constant H. Never chroma 0 on a neutral, because flat grey
beside a tinted accent looks wrong.

| Layer | Light | Dark |
|---|---|---|
| Paper, base | `oklch(96-98% 0.005-0.015 H)` | `oklch(12-18% 0.008-0.015 H)` |
| Ink, text | `oklch(16-22% 0.005-0.015 H)` | `oklch(92-96% 0.005-0.01 H)` |
| Neutrals, 5 to 9 steps, 6 to 10% lightness apart | chroma 0.005-0.018 | same |
| Accent, exactly one | chroma 0.12-0.22 | see the dark derivation below |

## Worked four-layer palette, anchor hue 80, light mode

```css
:root {
  --color-paper:   oklch(96% 0.012 80);
  --color-paper-2: oklch(93% 0.014 80);
  --color-rule:    oklch(82% 0.010 80);
  --color-neutral: oklch(56% 0.008 80);
  --color-muted:   oklch(40% 0.008 70);
  --color-ink:     oklch(18% 0.010 60);
  --color-focus:   oklch(55% 0.19  55);
}
```

Neutral steps move 6 to 10% in lightness and keep chroma 0.005 to 0.018 toward
the anchor. No source gives a reason for that step size.

## Twelve-step ramp, base `oklch(0.60 0.20 250)`

```css
:root {
  --blue-1:  oklch(0.99 0.01 250);
  --blue-2:  oklch(0.96 0.02 250);
  --blue-3:  oklch(0.93 0.04 250);
  --blue-4:  oklch(0.90 0.06 250);
  --blue-5:  oklch(0.86 0.08 250);
  --blue-6:  oklch(0.80 0.10 250);
  --blue-7:  oklch(0.73 0.13 250);
  --blue-8:  oklch(0.64 0.18 250);
  --blue-9:  oklch(0.55 0.20 250);
  --blue-10: oklch(0.49 0.19 250);
  --blue-11: oklch(0.43 0.15 250);
  --blue-12: oklch(0.25 0.08 250);
}
```

Hold H, sweep lightness from 0.99 down to 0.25, chroma low at both ends and
peaking at steps 8 and 9. No `lighten()` call, no opacity trick.

| Steps | Role | Lightness |
|---|---|---|
| 1 to 5 | backgrounds: app, subtle, element, hover, active | 0.99 down to 0.86 |
| 6 to 7 | borders: subtle, then default and focus | 0.80 down to 0.73 |
| 8 to 10 | solids: badge, primary, primary hover | 0.64 down to 0.49 |
| 11 to 12 | text: low contrast, then high contrast | 0.43 down to 0.25 |

Interaction states are already in the ramp: hover background step 4, active 5,
focus border 7, primary solid 9, solid hover 10.

The lightness column is read off the worked ramp above. Where the source's own
role-map column disagrees, the ramp wins. references/evidence.md carries both
sets and the reason.

The ramp shape is credited to Radix. The chroma curve follows from gamut
behaviour, not from a stated rule.

## The same ramp on a dark ground, our selection

Used unchanged on 12 to 18% paper, step 4 is a near-white hover background and
step 12 is invisible as text, so the ramp is rebuilt, not reused. No pack
derives a dark form of it, so references/evidence.md reconciles the walk below
against Radix's published `blueDark` scale and names the two gaps it leaves.

The selection: walk the ramp from the dark end. Step numbers, roles and
interaction states do not move, so every rule written against the light ramp
still reads. Hold H. Sweep lightness up, from the dark paper band at step 1 to
the ink band at step 12. Keep the chroma peak at steps 8 and 9, down 0.02 to
0.04 from the light ramp, which is the accent operation in the dark derivation
below. Step 9 lands 5 to 10 lightness points above the light step 9, the other
half of that operation.

```css
:root[data-theme="dark"] {
  --blue-1:  oklch(0.17 0.01 250);
  --blue-2:  oklch(0.21 0.02 250);
  --blue-3:  oklch(0.25 0.04 250);
  --blue-4:  oklch(0.29 0.06 250);
  --blue-5:  oklch(0.33 0.08 250);
  --blue-6:  oklch(0.39 0.10 250);
  --blue-7:  oklch(0.46 0.13 250);
  --blue-8:  oklch(0.55 0.15 250);
  --blue-9:  oklch(0.62 0.17 250);
  --blue-10: oklch(0.68 0.16 250);
  --blue-11: oklch(0.80 0.10 250);
  --blue-12: oklch(0.94 0.04 250);
}
```

Only the direction of the sweep is ours.

## The accent budget

One accent, spent on about 3% of the viewport. It is a highlighter, and
overusing it is the default this file exists to stop. Budget it while writing
the CSS: 3% is an author's figure, not something readable off a screenshot.

Semantic colour, good, warning and critical, is a separate set from the accent
ramp. It spends neither the one-accent budget nor the 3% viewport figure.
`artifact-design` says the same.

## The eight states

Every interactive element gets eight states styled: default, hover, focus,
active, disabled, loading, error, and the filled or selected state. Model
output styles two, default and hover, then stops. Read the state colours off
the ramp, per the role map above.

Border width is identical in every state. State changes go to background
colour, outline or box shadow. Changing border width on focus shifts the layout
by a pixel and the eye catches it. Never transition `border-width`, `padding`
or `height`, for the same reason.

Disabled is three independent signals, not one: `opacity: 0.55`,
`cursor: not-allowed` and `aria-disabled="true"`, plus a muted placeholder
colour. A user who misses one still gets the state. One source's summary table
says 0.5 and its own detailed recipe says 0.55; take 0.55.

Hover styles carry the `@media (hover: hover)` guard in references/motion.md.

## Second hue by rotation

Complementary is H plus 180, maximum contrast. Triadic is H plus 120 and 240.
Analogous is H plus or minus 30, low contrast and safe. Split complementary, H
plus 150 and H plus 210, keeps most of the complementary contrast without the
harshness.

Two accents at the very most, and one is the normal answer.

## Three token tiers

1. Primitive: the raw ramp, `--color-blue-500`.
2. Semantic: a role pointing at a primitive, `--color-interactive`.
3. Component: a specific binding, `--button-bg-primary`.

Theme switching moves tier 2 only, re-branding moves tier 1 only, and a
per-component exception stays in tier 3 where it cannot leak.

## Dark derivation

Derive dark from light. Do not invert.

| Operation | Value |
|---|---|
| Paper lightness | 12 to 18% |
| Ink lightness | 92 to 96% primary, about 65% secondary |
| Accent chroma | down by 0.02 to 0.04, or 15 to 25% |
| Accent lightness | up by 5 to 10% |
| Elevation | up about 3% lightness per level |
| Body font weight | down 50 units, so 400 becomes 350 |
| Hue | unchanged between modes |

Reasons: bright text on pure black smears on OLED and the extreme contrast
tires the eye, so paper never reaches 0. A drop shadow is invisible on a dark
surface, so lightness carries depth. Light text on a dark ground looks heavier
at the same weight, which the 50-unit drop compensates for. An accent balanced
against white looks garish against near-black.

One pack offers a hue-temperature preference for dark grounds with no reason
attached: cool 250 to 270 for developer tools and fintech, warm 50 to 80 for
editorial and reading.

`artifact-design` owns the theme-switching mechanics, including the three-state
light, dark and system contract. Follow that file for the mechanism and this
one for the values.

## Contrast checking

Check contrast in OKLCH. sRGB hex checkers drift near the extremes. Padding
counts toward a tap target, so a 16px icon inside a 44px hit area passes while
a bare 16px icon link fails. The floors are in references/thresholds.md.
