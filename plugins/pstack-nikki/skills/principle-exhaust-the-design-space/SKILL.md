---
name: principle-exhaust-the-design-space
description: Use when two or three plausible designs must be built and judged side by side before one is committed to, and no precedent in the codebase settles it, for instance a novel interaction, a mechanic that lives or dies on feel, a look-dev direction, or an architecture with several viable shapes. Requires competing candidates and an explicit comparison. One throwaway sketch answering a single design question is the `prototype` skill instead.
---

# Exhaust the design space

Novel decision, no established precedent -> explore several concrete
alternatives before implementing. Building wrong thing cost more than exploring
three options.

Right answer not obvious -> build 2-3 competing prototypes or sketches. Compare
side by side. Only then commit. Design it twice, by another name. Second flavour
of the first shape does not count: options must differ in SHAPE, not parameter.

Make comparison cheap and concrete:

- Same input, same harness, outputs next to each other.
- Judge on criteria named BEFORE looking: feel, cost, blast radius, cost to
  delete later.
- Keep losing prototypes until choice locked. They are the evidence.

## Applies

- Novel interaction or mechanic where feel decide, no prior art in repo.
- Architecture with several viable shapes.
- Product decision resting on experience, not logic.

## Does not apply

- Mechanical implementation where pattern already established in repo.
- Bug fix or refactor with clear target state.
- Constraints dictate a single viable approach.
- Prototype cost exceed cost of being wrong -> pick one, keep it reversible.
