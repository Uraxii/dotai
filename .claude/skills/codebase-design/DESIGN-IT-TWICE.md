# Design It Twice

Exploring alternative interfaces for a chosen deepening candidate.

Why design twice, when it earns its cost, and how to judge candidates against
criteria named before looking: the `principle-exhaust-the-design-space` skill.
This file carries only what is specific to running it with sub-agents on a
module interface.

Uses the vocabulary in [SKILL.md](SKILL.md), **module**, **interface**,
**seam**, **adapter**, **leverage**.

## Before spawning

Write the problem space out for the user: the constraints any new interface
must satisfy, the dependencies it relies on and which category each falls into
(see [DEEPENING.md](DEEPENING.md)), and a rough illustrative code sketch to
make the constraints concrete. The sketch is not a proposal.

Show it, then spawn immediately. The user reads and thinks while the sub-agents
work.

## The sub-agent briefs

Spawn 3+ in parallel. Each must produce a **radically different** interface,
not a variant of one shape.

Each brief is technical and independent of the user-facing writeup above: file
paths, coupling details, dependency category from [DEEPENING.md](DEEPENING.md),
what sits behind the seam. Include both [SKILL.md](SKILL.md) vocabulary and
CONTEXT.md vocabulary so every agent names things consistently with the
architecture language and the project's domain language.

One design constraint per agent:

- Agent 1: "Minimize the interface: aim for 1-3 entry points max. Maximise leverage per entry point."
- Agent 2: "Maximise flexibility: support many use cases and extension."
- Agent 3: "Optimise for the most common caller: make the default case trivial."
- Agent 4 (if applicable): "Design around ports & adapters for cross-seam dependencies."

Each sub-agent outputs:

1. Interface (types, methods, params: plus invariants, ordering, error modes)
2. Usage example showing how callers use it
3. What the implementation hides behind the seam
4. Dependency strategy and adapters (see [DEEPENING.md](DEEPENING.md))
5. Trade-offs: where leverage is high, where it's thin

## Comparing

Present designs sequentially so the user can absorb each one, then contrast
them in prose on the three axes that matter here: **depth** (leverage at the
interface), **locality** (where change concentrates), and **seam placement**.

Then give your own recommendation. Be opinionated: which design is strongest
and why. Propose a hybrid if elements from different designs combine well. The
user wants a strong read, not a menu.
