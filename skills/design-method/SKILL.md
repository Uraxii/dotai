---
name: design-method
description: >-
  Derive design values before writing any web page, artifact, or UI, then
  render it and inspect the pixels for named AI tells. Use for a landing page,
  dashboard, report page, mockup, restyle, or any complaint that a page looks
  machine-made. Supplies the numbers `artifact-design` leaves to taste.
---

# Design method

Web and artifact work only. Native game UI is out of scope. Load
`artifact-design` too. It owns the prohibitions, the theming contract and the
copy rules, none repeated here.

## 1. Read three inputs off the brief

Every mode starts here. Write all three down first. Job: the nouns in the
request, such as dashboard, landing page or tool. Mood: any colour word, brand
hex or adjective. Treatment: utilitarian for a plan, memo, demo, report,
review or internal document, editorial for a landing page, a game, or an app
or tool someone keeps and shares. When both fit the subject decides, and
seriousness beats longevity: anything carrying an incident, outage, failure or
severity is utilitarian however long it is kept. That tiebreak is ours.
Neither fits: utilitarian. Job picks the type ratio and the fallback hue, mood
picks the hue, treatment sets how far the layout goes.

## 2. Pick a mode

| Situation | Mode |
|---|---|
| build a page or artifact from a brief | modes/new-page.md |
| change values on a page that exists | modes/restyle.md |
| "this looks AI-generated", or a page to check | modes/diagnose.md |

## 3. Open one reference per decision

| Subsystem | File |
|---|---|
| ratio, ladder, headline size, weight, measure | references/type.md |
| hue, four layers, ramp, eight states, dark | references/color.md |
| spacing, density, grid, overflow | references/space-and-layout.md |
| duration, easing, choreography, caps, reduced motion | references/motion.md |
| contrast, text size and tap-target floors | references/thresholds.md |
| capture, fresh critic, verdict table | references/critique.md |
| licences, weak claims, empty areas | references/evidence.md |

## Two sanctioned overrides of `artifact-design`

These two only. The rest of that skill holds.

1. It says "**Write, look once, publish**" and "Don't build a test loop around
   your own file: no repeated screenshots". The critique step overrides both:
   one look catches a tell but cannot confirm the fix, so the bound is two
   recapture rounds, not zero.
2. It rules pure white and near-black grounds fine. Dark paper here never
   reaches 0% lightness, for the source's reason in references/color.md. On
   light it wins, so read 96 to 98% as a default, not a ban on white.

## The critique step always runs

Every mode ends at references/critique.md, and you never fill its verdict
table. A fresh agent that never saw your HTML fills it from the captured PNGs,
marking each tell present, absent, or not-captured when the frames cannot say,
and citing what in the image decided it. The model that chose the layout is
the worst reader of whether the layout is a tell.

## What this rests on

No source pack ran a controlled test, so these numbers are specific and
internally consistent, not measured, and the strongest output evidence in the
corpus runs against the packs. references/evidence.md holds that, the
licences, and the six rulings that are ours rather than extracted method.
