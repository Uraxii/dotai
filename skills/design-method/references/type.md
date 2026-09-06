# Type

## Ratio and density by job

| Job | Ratio | Density |
|---|---|---|
| dashboard, admin, analytics, monitoring, developer tool | 1.2 | dense |
| app, tool, SaaS, fintech, e-commerce | 1.25 | medium |
| landing page, portfolio, editorial, healthcare, luxury | 1.333 | spacious |
| report, review, postmortem, status page | 1.25 | medium |
| no row above matches | 1.25 | medium |

The last two rows are ours. The source names no ratio for an unclear job and
defaults to 1.25 by habit. The density column feeds
references/space-and-layout.md.

## The ratio set

| Ratio | Interval | Suits |
|---|---|---|
| 1.2 | none named at source | conservative, dense data |
| 1.25 | major third | balanced, most sites |
| 1.333 | perfect fourth | dramatic, landing pages, editorial |
| 1.5 | perfect fifth | |
| 1.618 | golden ratio | |

A constant multiplier keeps every step distinct. Fixed increments of a few
pixels produce a slope nobody reads as hierarchy.

## Fixed ladder, ratio 1.25 from a 16px body

```css
:root {
  --text-xs:      0.64rem;    /* 10.24px, 1.25^-2 */
  --text-sm:      0.8rem;     /* 12.8px,  1.25^-1 */
  --text-base:    1rem;       /* 16px,    body    */
  --text-md:      1.25rem;    /* 20px             */
  --text-lg:      1.5625rem;  /* 25px             */
  --text-xl:      1.9531rem;  /* 31.25px          */
  --text-2xl:     2.4414rem;  /* 39.06px          */
  --text-3xl:     3.0518rem;  /* 48.83px          */
  --text-4xl:     3.8147rem;  /* 61.04px          */
  --text-display: clamp(2.75rem, 5vw + 1rem, 5.25rem);
}
```

Every step is the one before it times 1.25. Emit all nine named properties,
`--text-xs` through `--text-4xl`, plus the display clamp. Never type a raw size
in a rule. Body is `1rem`, 16px, the floor in references/thresholds.md. For a
different ratio, regenerate the ladder rather than hand-picking sizes near it.
A list of round numbers such as 16, 20, 24, 32, 40 has step ratios of 1.25,
1.2, 1.333 and 1.25, so it is a hand-picked list wearing the word ratio.

## Fluid ladder

The alternative interpolates between a small and a large viewport, so no media
query is needed. Carry the generating inputs in a comment beside the output, so
a later agent regenerates the ladder instead of guessing. The values below came
from 320px to 1240px viewport, 16px to 18px base, ratio drifting 1.2 to 1.25.
No source explains the drift.

```css
:root {
  --step--2: clamp(0.69rem, 0.66rem + 0.18vw, 0.80rem);
  --step--1: clamp(0.83rem, 0.78rem + 0.25vw, 1.00rem);
  --step-0:  clamp(1.00rem, 0.93rem + 0.33vw, 1.13rem); /* body */
  --step-1:  clamp(1.20rem, 1.10rem + 0.45vw, 1.41rem);
  --step-2:  clamp(1.44rem, 1.30rem + 0.63vw, 1.76rem);
  --step-3:  clamp(1.73rem, 1.54rem + 0.88vw, 2.20rem);
  --step-4:  clamp(2.07rem, 1.81rem + 1.23vw, 2.75rem);
  --step-5:  clamp(2.49rem, 2.13rem + 1.69vw, 3.43rem);
}
```

Pick one ladder as the base. The fixed one tops out near 61px and the fluid one
near 55px, so stacking both gives two conflicting scales.

## Display cap and its exceptions

88px, 5.5rem, is the cap. Above it a hero crowds itself at 1280px to 1440px and
wraps as drama rather than weight. A 1.333 ladder overshoots the cap at its
ninth step, so clamp rather than round the ratio down. The `--text-display`
clamp above sits under the cap by construction.

The cap is the rule and the two exceptions are the source's. A poster-style
theme may reach 96px. A single-line, single-word display of 12 characters or
fewer may reach 7rem.

## Headline size by character count

Count the characters in the `h1`, then size it. The source names a display
headline near 100 characters as one of three tells it calls most reliable. 90
is where this table turns over.

| Characters | Size |
|---|---|
| 20 or fewer | display size; a single word may take the 7rem exception |
| 21 to 50 | display size; step down if it wraps past two lines at 414px |
| 51 to 90 | one rung down |
| over 90 | rewrite it shorter, or cap at `--text-4xl` with tighter leading |

The buckets assume a full-width track. In a narrow column the `h1` wraps
sooner, so read the wrap off its own track.

## Leading and weight

Body 1.5 to 1.65, headings 1.05 to 1.2. Under 1.5 body lines cramp, over 1.7
the paragraph stops cohering. All-caps display has no descenders, so its floor
is `line-height: 1.0` and its band 1.02 to 1.08. Below 1.0 the cap tops collide
with the baseline above.

Heading and body weight differ by at least 300 units: 300/700, 350/800 or
400/900. Habitual model output is body 400 with headings 600, a 200-unit gap
barely visible at heading sizes, so the page reads as unstyled rather than as
having a hierarchy. Use one weight for body text and reserve bold for emphasis.

## Tracking

| Text | Tracking |
|---|---|
| display and large headings | `-0.02em` to `-0.04em`, by how the face behaves |
| uppercase labels and small caps | `0.08em` to `0.14em` |
| body copy | never above `0.05em` |

Only the uppercase rule has a reason: untracked uppercase reads as cramped.
The two sources disagree on the band, one giving 0.08 to 0.14em and the other
0.05 to 0.1em. The row above takes 0.08em as the floor because it satisfies
both.

## Measure

45 to 75 characters is comfortable. Set `max-width: 65ch` by default. Past
roughly 75 the eye loses its place on the return sweep. `artifact-design`
already carries the 65ch figure. The addition here is the lower bound: a column
under 45 characters is also wrong.

## Families and size count

At most three families: one display, one body, and one outlier used in at most
two places. Two is the normal answer. Four reads as slop. Monospace counts.
Weights of one family do not. Reach for the outlier a third time and it has
become a second body font.

At most five sizes on one page, for which the sources give no reason.

Load the real weight file. Never rely on synthesised bold.
