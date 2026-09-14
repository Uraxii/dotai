---
name: principle-redesign-from-first-principles
description: Use when a new requirement lands on a design that already exists and the cheap move is to bolt it on beside the current shape with a flag, an extra branch, or a second registry. Rebuilds the design as if the requirement had been known on day one, then delivers that in increments.
---

# Redesign from first principles

New requirement arrive -> do not bolt onto existing design. Redesign as if the
requirement had been there from the start. Result should look like what you
would have built knowing it on day one.

## Method

1. Read all affected files. Understand current design whole, not just the touch
   point.
2. Ask: writing this from scratch, with this requirement known, what would we
   build?
3. Name the gap between that and the current shape. The gap IS the work.
4. Propagate through EVERY reference: types, callers, scene and resource files,
   tests, docs, examples, rationale text.
5. Think holistically, deliver incrementally. Big think, small commits.

## Bolt-on smells

- New optional param defaulting to old behaviour, forever.
- Parallel branch: `if new_mode:` sitting beside the old path.
- Second registry, manifest, or config holding the same kind of thing as the
  first.
- Requirement handled at every call site instead of inside the thing itself.

Design exist and requirement is new -> this skill. No precedent at all and the
shape itself unknown -> `principle-exhaust-the-design-space` first, then back
here.
