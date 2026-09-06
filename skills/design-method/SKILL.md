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
and artifact work only; native game UI is out of scope.

## 1. Read three inputs off the brief

Job: the nouns in the request, such as dashboard, landing page or tool. Mood:
any colour word, brand hex or adjective. Treatment: utilitarian for a plan,
memo, demo, report, review or internal document; editorial for a landing page,
a game, or an app or tool someone keeps and shares. When both readings fit, the
subject decides, and the seriousness of the subject beats the longevity of the
artifact: anything carrying an incident, an outage, a failure or a severity is
utilitarian however long it is kept. That tiebreak is ours. Neither fits:
utilitarian. Job sets step 2, mood sets step 4, treatment sets how far step 5
goes. Write all three down before starting.

## 2. Type ladder

| Job | Ratio | Density |
|---|---|---|
| dashboard, admin, analytics, monitoring, developer tool | 1.2 | dense |
| app, tool, SaaS, fintech, e-commerce | 1.25 | medium |
| landing page, portfolio, editorial, healthcare, luxury | 1.333 | spacious |
| report, review, postmortem, status page | 1.25 | medium |
| no row above matches | 1.25 | medium |

The last two rows are ours: the source routes an unclear job to medium density,
names no ratio for it, and defaults to 1.25 elsewhere by habit.

Body is `1rem`, 16px, also the accessibility floor in step 7. Each step up
multiplies by the ratio, each step down divides. Emit nine named properties,
`--text-xs` through `--text-4xl`; never type a raw size in a rule. Cap display
type at 5.5rem, 88px, because above it a hero crowds itself between 1280px and
1440px wide. A 1.333 ladder overshoots the cap at its ninth step, so clamp
rather than round the ratio down. The default
`clamp(2.75rem, 5vw + 1rem, 5.25rem)` sits under the cap by construction. The
cap is the rule and the source allows two exceptions to it: a poster-style
theme may reach 6rem, and a single-line, single-word display of 12 characters
or fewer may reach 7rem. At most five sizes per page, for which the sources
give no reason, and at most three families, because four families reads as
slop. Ladders, tracking, measure, families: references/type.md.

## 3. Headline, leading, weight

Count the characters in the `h1`, then size it. The source calls a display
headline near 100 characters the most reliable single tell in the material, and
90 is where the table below turns over.

| Characters | Size |
|---|---|
| 20 or fewer | display size; a single word may take the 7rem exception |
| 21 to 50 | display size; step down if it wraps past two lines at 414px |
| 51 to 90 | one rung down |
| over 90 | rewrite it shorter, or cap at `--text-4xl` with tighter leading |

The buckets assume the `h1` spans a full-width track. In a narrow grid column
it wraps sooner, so read the wrap off the track it sits in.

Leading: body 1.5 to 1.65, headings 1.05 to 1.2, all-caps display 1.02 to 1.08.
Heading and body weight differ by 300 units or more: 300/700, 350/800 or
400/900. The reasons, tracking and the all-caps floor: references/type.md.

## 4. Palette

Work in OKLCH: one lightness number means the same apparent brightness across
hues, and hue holds as you lighten. HSL does neither. Anchor hue H comes from a
named colour converted to OKLCH with chroma clamped to 0.12 to 0.20. With no
colour named, read H off the mood: warm 30 to 60, technical or industrial 220
to 250, botanical 130 to 160, late night or neon 280 to 320, amber 60 to 80.
Three fallbacks, ours, because the sources give none: a mood word missing from
that list or no mood at all gives H 250; a word naming a light level, such as
dark or night, sets the default theme and never the hue; two hue words, take
the first stated. Emit four layers at constant H, and never chroma 0 on a
neutral, because flat grey beside a tinted accent looks wrong.

| Layer | Light | Dark |
|---|---|---|
| Paper, the base surface | `oklch(96-98% 0.005-0.015 H)` | `oklch(12-18% 0.008-0.015 H)` |
| Ink, primary text | `oklch(16-22% 0.005-0.015 H)` | `oklch(92-96% 0.005-0.01 H)` |
| Neutrals, 5 to 9 steps, 6 to 10% lightness apart | chroma 0.005-0.018 | same |
| Accent, exactly one | chroma 0.12-0.22 | chroma minus 0.02 to 0.04, lightness plus 5 to 10% |

`artifact-design` rules pure white and near-black fine grounds. This skill
overrides that on dark only, its second and last override: dark paper never
reaches 0% lightness, for the source's reason in references/color.md. On a
light ground `artifact-design` wins, so read 96 to 98% as a default, not a ban
on white. Semantic colour, good, warning and critical, sits outside the accent
budget and is not the one accent, which agrees with `artifact-design` too.

Then emit the twelve-step accent ramp: hold H, sweep lightness 0.99 down to
0.25, keep chroma low at both ends and peak it at steps 8 and 9. Steps 1 to 5
are backgrounds, 6 to 7 borders, 8 to 10 solids, 11 to 12 text. The interaction
states are already in there: hover background step 4, active 5, focus border 7,
primary solid 9, solid hover 10. No lighten() call, no opacity trick. On a dark
ground the sweep runs from the dark end up and the step numbers and roles hold;
no source derives a dark ramp, so that walk and its values are ours. The accent
covers 3% or less of any viewport, because it is a highlighter and overusing it
is the default this step exists to stop. Style every interactive element in all
eight states, not the usual two: default, hover, focus, active, disabled,
loading, error, and filled or selected. Ramp values, the dark ramp, the state
rules, token tiers and hue rotations: references/color.md.

## 5. Spacing, density, layout

Spacing is ten named steps on a 4px base: 2, 4, 8, 12, 16, 24, 40, 64, 96,
144px. `artifact-design` already tells you to let layout do the spacing, and
that rule is what makes the ladder usable: gaps go on the container, `margin`
stays for optical nudges. Mix small, medium and large gaps, because a page where
every gap is 24px reads as a template. Density from step 2 is an operator on the
one ladder: dense shifts every value one step down, spacious one step up, medium
leaves it. Grid with `repeat(auto-fit, minmax(min(280px, 100%), 1fr))`. That
exact line is ours, welded from two packs' versions. The `min()` guard is load
bearing: without it the track cannot shrink and the layout overflows on a narrow
screen. Break the equal-column default at least once, with unequal tracks such
as `1.2fr 1fr 0.8fr`, a differing span, or one item spanning two columns. Pick a
primary axis; centred is what you get when nobody chose. Fluid ladders,
per-density padding, z-index and flatness fixes: references/space-and-layout.md.

## 6. Motion

Duration by case, not by feel: 50ms toggle or checkbox, 100ms tooltip or chip,
200ms default transition, 300ms modal or panel, 400ms page-level move, 600ms
deliberate reveal. Focus states, keyboard navigation and error appearance
animate at 0ms on purpose. A different source bands durations instead of fixing
them, and carries the only perceptual reason in this material, that anything
inside 80 to 120ms reads as immediate. Its bands are not these tokens, so read
them in references/motion.md rather than mixing the two sets.
Easing by case: entering `cubic-bezier(0, 0, 0.2, 1)`, leaving
`cubic-bezier(0.3, 0, 1, 0.3)`, moving between states
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
its first override of two. One look catches a tell but cannot confirm the fix,
so the bound is two recapture rounds, not zero. The rest of `artifact-design`
still holds. Run references/critique.md in full: it carries the capture and
theme-copy commands verified on this machine, the tell list and the verdict
table. The verdict is written, marks each tell present or absent, and cites what
in the image decided it. Never score your own page.

## Rulings and evidence

Six rulings here are ours rather than extracted method, labelled where each
appears: the treatment tiebreak in step 1, the two added rows in step 2, the
three mood fallbacks in step 4, the dark walk of the accent ramp, the grid line
in step 5, and the overshoot ban in references/motion.md. Border radius, icon
sizing and light-mode shadow derivation have no method in any source and none
is invented here; spend those three by role, per `artifact-design`. No source
pack published a controlled test, so these numbers are worth using for being
specific and internally consistent, not because anyone measured them.
references/evidence.md carries the licences and credits, every claim resting on
self-attested evidence, and every place a source contradicts itself. Read it
before quoting a figure here as fact.
