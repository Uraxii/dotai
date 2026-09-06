---
name: design-method
description: >-
  Turn a brief into emitted design values before writing any web page,
  artifact, or UI, then render it and inspect the pixels for named AI tells.
  Use for a landing page, dashboard, report page, mockup, restyle, or any
  complaint that a page looks machine-made. Supplies the numbers
  `artifact-design` leaves to taste.
---

# Design method

Run the steps in order. Each ends in a value you can paste into CSS. Stop only
when step 8 returns a written verdict. Load `artifact-design` too: it owns the
prohibitions, the theming contract and the copy rules, none repeated here. Web
and artifact work only; native game UI is out of scope. No source pack ran a
controlled test, so these numbers are specific and internally consistent rather
than measured, and the strongest output evidence in the corpus runs against the
packs; references/evidence.md holds it.

## 1. Read three inputs off the brief

Job: the nouns in the request, such as dashboard, landing page or tool. Mood:
any colour word, brand hex or adjective. Treatment: utilitarian for a plan,
memo, demo, report, review or internal document; editorial for a landing page, a
game, or an app or tool someone keeps and shares. When both fit, the subject
decides, and its seriousness beats the artifact's longevity: anything carrying
an incident, outage, failure or severity is utilitarian however long it is kept.
That tiebreak is ours. Neither fits: utilitarian. Job sets steps 2 and 4, mood
step 4, treatment how far step 5 goes. Write all three down first.

## 2. Type ladder

| Job | Ratio | Density |
|---|---|---|
| dashboard, admin, analytics, monitoring, developer tool | 1.2 | dense |
| app, tool, SaaS, fintech, e-commerce | 1.25 | medium |
| landing page, portfolio, editorial, healthcare, luxury | 1.333 | spacious |
| report, review, postmortem, status page | 1.25 | medium |
| no row above matches | 1.25 | medium |

The last two rows are ours; the source names no ratio for an unclear job and
defaults to 1.25 by habit.

Body is `1rem`, 16px, also the accessibility floor in step 7. Each step up
multiplies by the ratio, each step down divides. Emit nine named properties,
`--text-xs` through `--text-4xl`; never type a raw size in a rule. Cap display
type at 5.5rem, 88px, because above it a hero crowds itself between 1280px and
1440px wide. A 1.333 ladder overshoots the cap at its ninth step, so clamp
rather than round the ratio down. The default `clamp(2.75rem, 5vw + 1rem,
5.25rem)` sits under the cap by construction. The cap is the rule; the source
allows a poster theme 6rem and a single-line word of 12 characters or fewer
7rem. At most five sizes per page, for which the sources give no reason, and at
most three families, because four reads as slop. Ladders, tracking, measure,
families: references/type.md.

## 3. Headline, leading, weight

Count the characters in the `h1`, then size it. The source names a display
headline near 100 characters as one of three tells it calls most reliable. 90 is
where the table below turns over.

| Characters | Size |
|---|---|
| 20 or fewer | display size; a single word may take the 7rem exception |
| 21 to 50 | display size; step down if it wraps past two lines at 414px |
| 51 to 90 | one rung down |
| over 90 | rewrite it shorter, or cap at `--text-4xl` with tighter leading |

The buckets assume a full-width track; in a narrow column the `h1` wraps sooner,
so read the wrap off its own track.

Leading: body 1.5 to 1.65, headings 1.05 to 1.2, all-caps display 1.02 to 1.08.
Heading and body weight differ by 300 units or more: 300/700, 350/800 or
400/900. The reasons, tracking and the all-caps floor: references/type.md.

## 4. Palette

Work in OKLCH: one lightness number means the same apparent brightness across
hues, and hue holds as you lighten. HSL does neither. Anchor hue H comes from a
named colour converted to OKLCH with chroma clamped to 0.12 to 0.20. With no
colour named, read H off the mood and clamp chroma tighter, to 0.12 to 0.16:
warm 30 to 60, technical or industrial 220 to 250, botanical 130 to 160, late
night or neon 280 to 320, sun-drenched or market 60 to 80 amber. Verified at
source.

No mood word, or one off that list: the job row from step 2 sets H. There is no
default hue, because a default hue is how every page comes out blue.

| Job row from step 2 | H |
|---|---|
| dashboard, admin, analytics, monitoring, developer tool | 235 |
| app, tool, SaaS, fintech, e-commerce | 145 |
| landing page, portfolio, editorial, healthcare, luxury | 45 |
| report, review, postmortem, status page | 70 |
| no row matched | name one outside 200 to 280, and the brief line it came from |

The bands are the source's; assigning a job to one is ours, and the spread is
the point. Two more fallbacks, ours: a word naming a light level, such as dark
or night, sets the default theme and never the hue; two hue words, take the
first. Emit four layers at constant H, and never chroma 0 on a neutral, because
flat grey beside a tinted accent looks wrong.

| Layer | Light | Dark |
|---|---|---|
| Paper, the base surface | `oklch(96-98% 0.005-0.015 H)` | `oklch(12-18% 0.008-0.015 H)` |
| Ink, primary text | `oklch(16-22% 0.005-0.015 H)` | `oklch(92-96% 0.005-0.01 H)` |
| Neutrals, 5 to 9 steps, 6 to 10% lightness apart | chroma 0.005-0.018 | same |
| Accent, exactly one | chroma 0.12-0.22 | chroma minus 0.02 to 0.04, lightness plus 5 to 10% |

`artifact-design` rules pure white and near-black grounds fine. This skill
overrides that on dark only, its second and last override: dark paper never
reaches 0% lightness, for the source's reason in references/color.md. On light
it wins, so read 96 to 98% as a default, not a ban on white. Semantic colour,
good, warning and critical, sits outside the accent budget and is not the one
accent.

Then emit the twelve-step accent ramp: hold H, sweep lightness 0.99 down to
0.25, keep chroma low at both ends and peak it at steps 8 and 9. Steps 1 to 5
are backgrounds, 6 to 7 borders, 8 to 10 solids, 11 to 12 text. The interaction
states are already in there: hover background step 4, active 5, focus border 7,
primary solid 9, solid hover 10. No lighten() call, no opacity trick. On a dark
ground the sweep runs from the dark end up and the step numbers and roles hold.
No design pack derives that walk; Radix's published dark scale does, and ours
sits within 0.04 lightness of it at every step, so it is a selection rather than
an invention. references/color.md carries the comparison and the one role-map
disagreement. Budget the accent at about 3% of the viewport while writing the
CSS: it is a highlighter, and overusing it is the default this step exists to
stop. An author's budget, not a figure readable off a screenshot. Style every
interactive element in all eight states, not the usual two: default, hover,
focus, active, disabled, loading, error, and filled or selected. Ramp values,
the dark ramp, the state rules, token tiers and hue rotations:
references/color.md.

## 5. Spacing, density, layout

Spacing is ten named steps on a 4px base: 2, 4, 8, 12, 16, 24, 40, 64, 96,
144px. `artifact-design` already says to let layout do the spacing, which makes
the ladder usable: gaps on the container, `margin` for optical nudges. Mix
small, medium and large gaps, because a page where every gap is 24px reads as a
template. Density from step 2 is an operator on the one ladder: dense shifts
every value one step down, spacious one step up, medium leaves it. Grid with
`repeat(auto-fit, minmax(min(280px, 100%), 1fr))`. anti-slop-design already
ships that guarded line with `auto-fill`; taking `auto-fit` instead is the whole
of our choice. The `min()` guard is load bearing: without it the track cannot
shrink and the layout overflows on a narrow screen. Break the equal-column
default at least once, with unequal tracks such as `1.2fr 1fr 0.8fr`, a
differing span, or one item spanning two columns. Pick a primary axis; centred
is what you get when nobody chose. Fluid ladders, per-density padding, z-index
and flatness fixes: references/space-and-layout.md.

## 6. Motion

Duration by case, not by feel: 50ms toggle or checkbox, 100ms tooltip or chip,
200ms default transition, 300ms modal or panel, 400ms page-level move, 600ms
deliberate reveal. Focus states, keyboard navigation and error appearance
animate at 0ms on purpose. A different source bands durations instead of fixing
them, and carries the only perceptual reason here, that anything inside 80 to
120ms reads as immediate. The fixed set wins because a band still leaves a
number to pick and this step hands one over; every token bar 50ms and 600ms sits
inside the matching band, so only the choice goes. Do not mix the sets; the
bands are in references/motion.md. Easing by case: entering `cubic-bezier(0, 0,
0.2, 1)`, leaving `cubic-bezier(0.3, 0, 1, 0.3)`, moving between states
`cubic-bezier(0.2, 0, 0, 1)`, `linear` for loops only. The browser default
`ease` is banned. An exit runs at 60 to 75% of its entrance, so a 300ms open
pairs with a 200ms close. Animate only `transform`, `opacity`, `filter` and
`clip-path`; the rest force a layout recalculation every frame. Stagger, caps
and the reduced-motion override: references/motion.md.

## 7. Threshold pass

Body text 4.5:1 contrast; large text, control edges, icons and focus rings 3:1;
body 16px and never under 14px; tap targets 44 by 44px, of which 24 by 24 is the
WCAG 2.2 floor and 44 is platform guidance, not law; one shared 44px control
height across inputs and adjacent buttons. Never rely on colour alone.

## 8. Critique the render. This step always runs

`artifact-design` says "**Write, look once, publish**" and "Don't build a test
loop around your own file: no repeated screenshots". This skill overrides both,
its first override of two: one look catches a tell but cannot confirm the fix,
so the bound is two recapture rounds, not zero. The rest of `artifact-design`
holds. Run references/critique.md in full for the capture and theme-copy
commands verified on this machine, the tell list and the verdict table. You do
not fill that table in. A fresh agent that never saw your HTML does, from the
captured PNGs, marking each tell present or absent and citing what in the image
decided it. Never judge your own page: the model that chose the layout is the
worst reader of whether the layout is a tell.

## Rulings and evidence

Six rulings are ours rather than extracted method, labelled where each appears:
the treatment tiebreak in step 1, the two added rows in step 2, the job-to-hue
fallback in step 4, the dark walk of the accent ramp, `auto-fit` in step 5, and
the overshoot ban in references/motion.md. Border radius, icon sizing and
light-mode shadow derivation have no method in any source; spend those three by
role, per `artifact-design`. references/evidence.md carries the licences, every
claim resting on self-attested evidence, the practitioner evidence running
against the packs, and every place a source contradicts itself.
