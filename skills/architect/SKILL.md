---
name: architect
description: "Settles system structure before any logic is written: types, function signatures, module boundaries, and TODO-stub skeletons that implementation later fills in. Use when non-trivial work would lock in the wrong shape if code came first, for new-system design, refactoring direction, technology evaluation, or architectural trade-off analysis."
---

# Architect

Design before implementing. Sketch types, function signatures, class shapes,
and module boundaries with TODO-stub bodies and pseudocode. Synthesize across
several models, hand the sketch to implementation as the contract, and throw it
out when implementation proves it wrong.

## Start

Open a todolist with one entry per phase before starting. Autonomous mode
needs the list to show phase position and keep phases from silently vanishing.

1. Ground
2. Sketch
3. Agree
4. Hand off
5. Scrap

## Phase A: Ground the problem

Build a real mental model of every system the new code touches. Run the `how`
skill over the relevant subsystems, in critique mode when existing structure is
the constraint or the design must push back on it. Naming a file is not
grounding: produce the traced model `how` prescribes. If the design redefines
ownership or layering, run the `why` skill on the existing shape too, so the
rationale becomes a constraint instead of a guess. Skip this phase only when
the work is greenfield with nothing to integrate with.

## Phase B: Sketch

Run the `arena` skill with the design-sketch task and the Phase A grounding
artifacts. Pass `references/runner-prompt.md` as each runner's prompt. Each
candidate produces a design package shaped per
`references/rationale-template.md`: the caller's usage first, then the type
sketch, signatures, module map, and the rationale derived from it. A TODO-stub
body at every call or change site (`raise NotImplementedError`, `throw new
Error("not impl")`) marks where logic goes.

Use `arena runners` from the `poteto-mode` skill's `models.md` when present;
row absent -> omit `model`.

Design it twice. Require at least two structurally distinct candidates before
synthesis, even when the first looks sufficient, per
`principle-exhaust-the-design-space`. Whole-shape alternatives, not point fixes
inside one shape. Screen each against
[`references/design-red-flags.md`](references/design-red-flags.md) first:
reject or revise shallow modules, information leakage, temporal decomposition,
and pass-through methods.

Compare viable candidates on interface depth. Prefer the design that hides more
complexity behind a smaller public surface. A rich interface keeps call chains
short by concentrating capability. Arena returns one synthesized package, whose
synthesis decision fills that section of the rationale.

## Phase C: Agree (opt-in)

Default: proceed to hand-off, no human checkpoint. Opt in when the invoker asks
("stop and show me before implementing"), then pause for sign-off.

The synthesis ships as its own commit either way. That is the scaffold-first
mode of `principle-foundational-thinking`, and later commits read as filling in
bodies against a stable contract. Planned, scoped breakage during fill-in is
fine, per `principle-outcome-oriented-execution`. For adversarial pressure
before implementation starts, run `interrogate` on the synthesized sketch. A
human pushing back on the shape, in a checkpoint or after the fact, is Phase A
evidence: re-ground and re-run Phase B before any more code.

## Phase D: Hand off to implementation

Architect stops at shape. Hand the synthesized sketch to a `developer` subagent
as the contract: replace TODO-stub bodies with code, pseudocode with logic.
Never write implementation logic, tests, config files, or deploy scripts
yourself. Deviations the developer hits are signal worth surfacing, not
friction to absorb silently. A function needing a parameter the sketch did not
anticipate means the sketch was wrong, a requirement was missed, or the
implementation overreaches. Surface it, do not bolt it on.

## Phase E: Scrap when the architecture is wrong

If implementation keeps producing friction the sketch cannot absorb, throw the
sketch out. Do not bolt fixes onto a wrong design, per
`principle-redesign-from-first-principles`. Fix the root cause instead. The
signal is a pattern, not single instances. Tells:

- The same shape of workaround appearing repeatedly across unrelated code.
- Multiple unrelated edge cases that all need special-case branches.
- Types that need escape hatches (`any`, casts, optional fields always set in
  practice) to compile.
- The "we need a lock" reflex when the sketch said the state was not shared.
- Callers having to know the abstraction's internal rules to use it.
- Two or more independent Phase D deviations of the same shape. Surfacing
  deviations is Phase D's job; a repeated pattern of them is Phase E's trigger.

Use judgment. A few edge cases do not condemn an architecture, and complexity
in the data is not complexity in the design.

When you scrap:

1. Re-run the `how` skill over what has been built. Implementation lessons
   enter the new design as inputs, not vibes.
2. Redesign as if the new constraints had been day-one assumptions, per
   `principle-redesign-from-first-principles`.
3. Subtract before adding, per the "Subtract first" section of
   `principle-code-quality`. The new sketch starts smaller than the old one.
4. Return to Phase B and re-run `arena`.

## Outputs

The caller's usage written first, the type sketch derived from it. One file of
new types and signatures for a small change; a module map plus type definitions
for larger work. Bodies stay TODO stubs. The rationale ships alongside per
`references/rationale-template.md`, with the usage sketch and synthesis
decision.
