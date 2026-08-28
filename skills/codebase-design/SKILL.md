---
name: codebase-design
description: Shared vocabulary for designing deep modules. Use when the user wants to design or improve a module's interface, find deepening opportunities, decide where a seam goes, make code more testable or AI-navigable, or when another skill needs the deep-module vocabulary.
---

# Codebase design

Design **deep modules**: a lot of behaviour behind a small interface, at a
clean seam, testable through that interface. Use this language wherever code is
designed or restructured.

## Glossary

Use these terms exactly. Do not substitute "component", "service", "API", or
"boundary". Consistent language is the whole point.

**Module**: anything with an interface and an implementation. Scale-agnostic on
purpose: a function, class, package, or tier-spanning slice. _Avoid_: unit,
component, service.

**Interface**: everything a caller must know to use the module correctly. The
type signature, plus invariants, ordering constraints, error modes, required
configuration, performance characteristics. _Avoid_: API, signature (too
narrow, type-level only).

**Implementation**: what is inside a module. Distinct from **Adapter**: a thing
can be a small adapter with a large implementation (a Postgres repo) or a large
adapter with a small implementation (an in-memory fake). Say "adapter" when the
seam is the topic, "implementation" otherwise.

**Depth**: leverage at the interface, the amount of behaviour a caller or test
can exercise per unit of interface it must learn. **Deep** = much behaviour
behind a small interface. **Shallow** = interface nearly as complex as the
implementation. Not a ratio of implementation lines to interface lines; that
rewards padding.

**Seam** _(Michael Feathers)_: a place where you can alter behaviour without
editing in that place; the location at which a module's interface lives. Where
to put the seam is its own decision, distinct from what goes behind it.
_Avoid_: boundary (overloaded with DDD's bounded context).

**Adapter**: a concrete thing satisfying an interface at a seam. Describes the
role it fills, not what is inside it.

**Leverage** and **Locality**: what depth buys. Callers get leverage, one
implementation paying back across N call sites and M tests. Maintainers get
locality, with change, bugs, knowledge, and verification concentrated in one
place instead of spread across callers.

## Principles

- Designing an interface, ask three things: can I reduce the number of methods,
  can I simplify the parameters, can I hide more complexity inside?
- **Depth is a property of the interface, not the implementation.** A deep
  module can be composed internally of small swappable parts; they just are not
  part of the interface. A module can have **internal seams** (private, used by
  its own tests) as well as the **external seam** at its interface.
- **The deletion test.** Imagine deleting the module. Complexity vanishes ->
  it was a pass-through. Complexity reappears across N callers -> it earned its
  keep.
- **The interface is the test surface.** Callers and tests cross the same seam.
  Wanting to test *past* the interface means the module is the wrong shape.
- **One adapter means a hypothetical seam. Two adapters means a real one.** Do
  not introduce a seam unless something actually varies across it.

- **Design for testability.** Accept dependencies, do not construct them
  inside. Return results, do not mutate through side effects. Keep the surface
  small: fewer methods is fewer tests, fewer params is simpler setup.

## Going deeper

- Deepening a cluster given its dependencies: [DEEPENING.md](DEEPENING.md).
- Exploring alternative interfaces: spawn 3+ subagents in parallel, one design
  constraint each (minimise the interface; maximise flexibility; optimise for
  the most common caller; ports and adapters for cross-seam dependencies).
  Each returns an interface, a usage example, what sits behind the seam, its
  dependency strategy, and its trade-offs. Compare on depth, locality, and seam
  placement, then give one opinionated recommendation, not a menu. Why and when
  it earns its cost: `principle-exhaust-the-design-space`.
