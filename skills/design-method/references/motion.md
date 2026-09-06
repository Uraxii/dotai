# Motion

## Duration by case

| Token | Value | Case |
|---|---|---|
| instant | 50ms | must feel immediate: checkbox tick, toggle |
| fast | 100ms | small transitions: tooltip appear, chip dismiss |
| normal | 200ms | the default: dropdown open, focus ring |
| moderate | 300ms | medium transitions: modal entry, panel slide |
| slow | 400ms | page-level transitions, complex choreography |
| deliberate | 600ms | high-emphasis moments: an onboarding reveal |

Four to six tokens is enough. Never more tokens than you have distinct cases.

A second source bands durations instead of fixing them, and carries the only
perceptual reason in this material: anything inside 80 to 120ms reads as
immediate.

| Band | Case |
|---|---|
| 80 to 120ms | instant feedback |
| 150 to 200ms | hover and focus |
| 250 to 300ms | a modal or sheet |
| 400 to 500ms | a toast or a section reveal |
| 0ms | focus states, keyboard navigation, errors |

0ms is there because plenty of things should not animate. The fixed table wins
over the bands: a band still leaves a number to pick, and this file hands one
over. Every token bar 50ms and 600ms sits inside the matching band, so only
the choice goes.

An alternative token set, if you prefer round numbers: 100ms, 160ms, 240ms,
360ms, 500ms. Pick one set. Never ship both, and never mix the fixed set with
the bands.

## Easing by case

| Token | Curve | Case |
|---|---|---|
| standard | `cubic-bezier(0.2, 0, 0, 1)` | elements moving between states |
| decelerate | `cubic-bezier(0, 0, 0.2, 1)` | elements entering |
| accelerate | `cubic-bezier(0.3, 0, 1, 0.3)` | elements leaving |
| linear | `linear` | looping only: spinners, shimmer |

A softer alternative set, from the other source: entering
`cubic-bezier(0.16, 1, 0.3, 1)`, leaving `cubic-bezier(0.7, 0, 0.84, 0)`,
symmetric toggles `cubic-bezier(0.65, 0, 0.35, 1)`, general
`cubic-bezier(0.4, 0, 0.2, 1)`.

Banned in both: the browser default `ease`, described as flat and uncrafted,
and `linear` outside progress bars and loaders.

## Overshoot, our ruling

`designer-skills` ships `cubic-bezier(0.34, 1.56, 0.64, 1)` as its spring curve
for playful or tactile interactions. `hallmark` bans that exact curve and calls
bounce dated. Both positions are self-attested taste. Neither pack ran a test.

Our ruling: functional UI gets no overshoot. Use it only where the brief asks
for a playful or brand-expressive moment, and then only on an element the user
is not waiting on. This is a decision, not extracted method.

## Choreography

Stagger a related group entering together by 30 to 50ms per item, most
important first. One source uses 80ms per index instead. Elements in one
semantic group share a duration and an easing. A group sliding in from the
right pairs with an outgoing group sliding out to the left. A staggered
sequence totals no more than 500ms.

An exit runs at 60 to 75% of its entrance. A 300ms entrance pairs with a 200ms
exit, never the reverse. No source states why.

## Caps and safety

At most three distinct animation primitives on one page. A counter, a hover
lift and a marquee is already three. Nothing over 2 seconds except a
continuous loop.

Animate `transform`, `opacity`, `filter` and `clip-path`, and nothing else.
`width`, `height`, `top`, `left`, `margin`, `padding`, `border-width` and
`font-size` each force a layout recalculation on every frame.

Under `prefers-reduced-motion: reduce`, override every duration token to 1ms
at the root, once, not component by component. Collapse spatial motion to an
opacity crossfade at 150ms or less and keep functional state changes intact.

Hover styles go inside `@media (hover: hover)`, or a hover style sticks after
a tap on a touch device.
