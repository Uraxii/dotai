---
name: experience-first
description: Use when cutting a feature list or scope, when choosing between one more option and polishing what already exists, when picking a default or preset someone else must live with, when the thing is easier to write than to call or operate, or when the answer to a design question is turning into make it configurable. Picks the tight core loop and the consumer's experience over more surface area.
---

# Experience first

Product IS the experience. Every technical decision help it or hurt it.
Implementation convenience conflict with consumer delight -> choose delight.

- **Say no to 1000 things.** Every feature, control, option must earn place.
- **Ship less, ship better.** Three polished features beat ten rough ones.
- **Prototype before committing.** Design decision cheaper in throwaway build
  than in production code.
- **Sweat detail.** Timing, alignment, spacing, feedback, failure state,
  default value.
- **Tighten core loop.** Feature serve the central workflow or get out of way.

## Consumer is whoever consume the work

- Game -> player. Frame timing, input feel, readability at speed.
- Art pipeline -> artist. One command, sane defaults, visible progress, output
  where expected.
- Infra or CLI -> operator. Error message naming the fix, idempotent rerun, no
  silent partial state.
- Library or API -> colleague who import it. Small surface, obvious call,
  honest types.
- Codebase -> next maintainer. Their experience count the same.

Explain impact from their seat, not from the implementation's.

Foundations serve the experience, not the reverse. `foundational-thinking`
govern the SEQUENCE of work; this one govern the TARGET.
