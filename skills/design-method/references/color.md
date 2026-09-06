# Colour

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

Neutral steps move 6 to 10% in lightness and keep chroma between 0.005 and
0.018 toward the anchor. No source gives a reason for that step size.

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

| Steps | Role | Lightness |
|---|---|---|
| 1 to 5 | backgrounds: app, subtle, element, hover, active | 0.99 down to 0.86 |
| 6 to 7 | borders: subtle, then default and focus | 0.80 down to 0.73 |
| 8 to 10 | solids: badge, primary, primary hover | 0.64 down to 0.49 |
| 11 to 12 | text: low contrast, then high contrast | 0.43 down to 0.25 |

The lightness column is read off the worked ramp above. The source states the
same role map with a different column, 0.97 to 0.83, 0.78 to 0.71, 0.64 to 0.44
and 0.43 to 0.22, next to that identical ramp. See the entry in
references/evidence.md; the ramp is the definition and the column follows it.

The ramp shape is credited to Radix. The chroma curve follows from gamut
behaviour rather than from a stated rule.

## The same ramp on a dark ground, our ruling

No source derives a dark form of the twelve-step ramp. Both packs derive dark
paper, ink, accent and elevation, and stop there. Used unchanged on a 12 to 18%
paper, step 4 is a near-white hover background and step 12 is invisible as text,
so the ramp has to be rebuilt rather than reused.

Our ruling: walk the ramp from the dark end. The step numbers and their roles do
not move, so every rule written against the light ramp still reads. Hold H.
Sweep lightness up instead of down, from the dark paper band at step 1 to the
ink band at step 12. Keep the chroma peak at steps 8 and 9, and take that peak
down 0.02 to 0.04 from the light ramp, which is the accent operation in the dark
derivation below. Step 9 lands 5 to 10 lightness points above the light step 9,
which is the other half of that same operation.

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

Roles, unchanged: 1 to 5 backgrounds, 6 to 7 borders, 8 to 10 solids, 11 to 12
text. Hover background is still step 4, active 5, focus border 7, primary solid
9, solid hover 10. Only the direction of the sweep is ours.

## The eight states

Every interactive element gets eight states styled: default, hover, focus,
active, disabled, loading, error, and the filled or selected state. The
observation behind the list is that model output styles two of them, default and
hover, and stops. Read the state colours off the ramp, per the role map above.

Two rules with mechanical reasons:

- Border width is identical in every state. State changes go to background
  colour, outline or box shadow. Changing border width on focus shifts the
  layout by a pixel and the eye catches it.
- Never transition `border-width`, `padding` or `height`, for the same reason.

Disabled is three independent signals, not one: `opacity: 0.55`,
`cursor: not-allowed` and `aria-disabled="true"`, plus a muted placeholder
colour. No single channel carries the whole meaning, so a user who misses one
still gets the state. One source's summary table says 0.5 and its own detailed
recipe says 0.55; take 0.55.

Hover styles go inside `@media (hover: hover)`, or a hover style sticks after a
tap on a touch device.

Semantic colour, good, warning and critical, is a separate set from the accent
ramp. It does not spend the one-accent budget and does not count toward the 3%
viewport figure. `artifact-design` says the same thing.

## Second hue by rotation

Complementary is H plus 180, maximum contrast. Triadic is H plus 120 and 240.
Analogous is H plus or minus 30, low contrast and safe. Split complementary is
H plus 150 and H plus 210, which keeps most of the complementary contrast
without the harshness.

Two accents at the very most, and one is the normal answer.

## Three token tiers

1. Primitive: the raw ramp, `--color-blue-500`.
2. Semantic: a role pointing at a primitive, `--color-interactive`.
3. Component: a specific binding, `--button-bg-primary`.

Theme switching moves tier 2 only, re-branding moves tier 1 only, and a
per-component exception stays in tier 3 where it cannot leak. Each kind of
change touches one layer.

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
surface, so lightness carries depth instead. Light text on a dark ground looks
heavier at the same weight, which is what the 50-unit drop compensates for. An
accent balanced against white looks garish against near-black.

One pack offers a hue-temperature preference for dark grounds with no reason
attached: cool 250 to 270 for developer tools and fintech, warm 50 to 80 for
editorial and reading.

`artifact-design` owns the theme-switching mechanics, including the three-state
light, dark and system contract. Follow that file for the mechanism and this
one for the values.

## Contrast checking

Check contrast in OKLCH. sRGB hex checkers drift near the extremes. Padding
counts toward a tap target, so a 16px icon inside a 44px hit area passes while
a bare 16px icon link fails.
