---
name: code-quality
description: Load before writing or changing code in any language, and before reviewing a diff, designing types or interfaces, refactoring, or debugging. Covers cross-language limits, naming, code smells, type and boundary discipline, domain modelling, reader load, deletion-first sequencing, and scope rules, plus on-demand references for Python, TypeScript, C#, GDScript, and Godot.
---

# Code quality (all languages, all vendors)

Repo's own documented standard always override this file. Skip anything the
repo's tooling already enforce.

## Language references

Working in one of these, read matching file on demand, not up front:
`references/python.md`, `references/typescript.md`, `references/csharp.md`,
`references/gdscript.md`, `references/godot.md`.

## Hard limits

- Function <=40 LoC. File <=600 LoC, one cohesive responsibility.
- Line <=80 chars (<=100 when readability win).
- Explicit return types. Function contracts stated.
- No bare catch/except. Handle errors explicit, per surrounding context.
- No magic numbers. Named constants carry domain + units.
- Guard clauses over deep nesting. Nesting >3 -> extract function.
- Compute or mutate, never both in same function.
- YAGNI. No dependency added without explicit approval.

## Match project

Read adjacent code first. Match naming, formatting, error handling, logging,
config, test patterns. Use utilities already there, never reinvent.

## Types and boundaries

Type checker is proof assistant. Defining errors out of existence beats adding
handlers.

- Illegal states unrepresentable: sum type over bag of optionals. `{done: bool,
  done_at?: T}` admit contradiction. Comment needed to say which field combo
  valid -> type too loose.
- Types are constructions, not restrictions: build shape that cannot hold bad
  value. Non-empty list = head + rest. Time range = start + duration.
- Brand semantic primitives: `UserId` vs `OrderId` not interchangeable.
  Validate once at creation, trust downstream.
- External data untyped until parsed (RPC, JSON, IPC, CLI args, config, env, DB
  rows): parse function per boundary -> typed model.
- Never lie to type checker. Cast, coercion, assert-not-null = deferred crash;
  trace each to its boundary, validate there.
- Exhaustive matching is compiler's job: new variant must break build. Derive
  types from authoritative schema (protobuf, OpenAPI, GraphQL, migration);
  hand-rolled parallel type drift.
- Strengthen type only where partiality appear, then stop. Prefer total
  functions; extra precision cost reuse, buy no safety.
- Validate and narrow AT boundary (CLI args, config, external API, network,
  storage); inside, trust types, propagate errors, no re-validation. Nil-check
  deep in call chain = noise, delete.
- Expose domain concepts across boundary, never transport/storage/framework
  types. Business logic = pure functions, no framework deps; shell thin.

## Model the domain

- Encode domain in structure, not scattered conditionals: state machine over
  loose booleans/phases/lifecycle flags, typed object over loose params or
  repeated shape assumption, map/registry/lookup table/discriminated union over
  branching spread across files, reducer or event model over ad-hoc mutation,
  queue/cache/index/tree when access pattern ask it.
- Module own one body of domain knowledge. Execution order is not ownership:
  load/validate/transform/save modules repeat same rules per step.
- Tells you skipped it: new feature grow if/else chain by one branch; second
  boolean must stay in sync with first.

## Reader load

- Guard two axes: layers to trace, state held in reader's head. Collapse layer
  not earning keep: one-caller wrapper, adapter with no second implementation,
  pass-through repeating same methods and args. Adjacent layers must change
  abstraction; broad interface hiding little complexity force reader to learn
  surface AND implementation.
- Shrink state scope: pure function > local > field > module state > global.
  Derive instead of sync. Name invariant once at boundary, not per consumer.
- Test: new reader answer "where X come from?" and "what can change X?" in
  under 30 seconds. No -> cut layers or cut state.

**Comments.** Comment restating code, narrating change, or apologizing for
workaround: delete, fix code instead. Workaround needing paragraph to justify -> code
wrong. Constraint comment ("do not remove", "ask X first") is unenforced rule:
encode as type, runtime check, test, or lint, then delete it. Suppression is
comment too; correctness or safety suppression must die, not be silenced. Keep
only comment about thing outside our control.

## Subtract first

- Remove before construct. Cut before polish. Leave design simpler behind same
  or smaller surface than found.
- Design for observed usage. No speculative validator, parser, guard beyond
  spec; out-of-spec feature drag guards behind it.
- New internal API: inventory callers, migrate, delete old API same wave. No
  compatibility layer kept for internal callers; temporary adapter exceptional
  and time-boxed. Move tests to new contract, delete tests pinning old
  implementation detail.

## Shared state and repeatability

- Concurrent writers: eliminate sharing first, each actor own its file, key,
  branch, dir, merged at read boundary. Sharing truly invariant -> serialize
  structurally (lockfile, sequential phase, single-writer owner, atomic
  compare-and-swap). Convention is not concurrency control.
- State-mutating op must converge: same end state run twice, or after crash at
  any point. Scan state, clean stale artifact, adopt live session, PID-based
  stale lock detection. "Depends what was left behind" -> add reconciliation.

## Debugging

- Reproduce first. Ask why until root cause; nil-check silencing crash is
  symptom fix. Fix pattern not instance: grep same shape, fix all. Stuck ->
  instrument, read actual error, never guess. "Broke after restart": suspect
  stale persistent state before code. Code not change between runs, state do.

## Sequencing work

- Smallest units each ending in checkable state, verified before next, never
  batched then verified once. Rebase onto clean trunk first.
- Order commits so sequence prove itself: failing test then fix, subtraction
  then reshape, scaffold then feature. Each unit land on its own.
- Non-trivial repeated work: build the lever (codemod, script, generator), not
  hand edits. First unit by hand to learn recipe, then tool, rerun on it, diff
  against hand-done version. Lever beats fanning out delegates.

## Smell baseline (Fowler, _Refactoring_ ch.3)

Applies even when repo document nothing. Each is a labelled heuristic
("possible Feature Envy"), never a hard violation. Reads *what it is* -> *fix*:

- **Mysterious Name**: name not reveal what it does or hold. -> rename; no
  honest name coming means design murky.
- **Duplicated Code**: same logic shape in more than one place. -> extract
  shared shape, call from both.
- **Feature Envy**: method reach into another object's data more than own. ->
  move method onto data it envy.
- **Data Clumps**: same few fields or params always travel together. -> bundle
  into one type, pass that.
- **Primitive Obsession**: primitive or string standing in for a domain
  concept. -> give concept its own small type.
- **Repeated Switches**: same switch/if-cascade on same type recurs. ->
  polymorphism, or one map both sites share.
- **Shotgun Surgery**: one logical change force scattered edits. -> gather what
  changes together into one module.
- **Divergent Change**: one module edited for several unrelated reasons. ->
  split so each change for one reason.
- **Speculative Generality**: abstraction or hooks for needs spec not have. ->
  delete, inline back until real need show.
- **Message Chains**: long `a.b().c().d()` the caller should not depend on. ->
  hide walk behind one method on first object.
- **Middle Man**: class or function that mostly delegate onward. -> cut it,
  call real target direct.
- **Refused Bequest**: subclass ignore or override most of what it inherit. ->
  drop inheritance, use composition.

## Code naming (engineering artifacts, all languages)

A name must reveal the thing's purpose to a reader with no other context. If it
only makes sense after reading the design discussion, it is wrong.

- Name the thing, not the mechanism. `controller entity` says how it is wired;
  `projectile` says what it is.
- Name the effect, not the metaphor or process. `change_owner` not
  `grant_control`. `restore_charge` not `handle_charge_event`.
- No scheduling/process words as identity: Deferred, Pending, Delayed, Async,
  Lazy describe when code runs, never what a thing is. `DeferredDeliverySystem`
  -> `ProjectileSystem`.
- No structure filler words as identity: Manager, Controller, Handler, Helper,
  Util, Service*, Data, Info, Object, Item. They describe code shape, not
  purpose. (*Service allowed only under an established subsystem convention,
  e.g. `EntityService`, and the prefix must still carry the meaning.)
- Prefer the plain domain word everyone already knows (projectile, hitbox,
  cooldown, teleport) over invented framework jargon. If the domain has a
  common word for it, use that word.
- Constants and fields carry domain + units: `REVIVE_TIME_SEC` not
  `TIME_EPSILON`. `cooldown_remaining` not `timer`.
- Applies everywhere a human reads: classes, members, funcs, signals, params,
  files, tests, diagrams, spec text, commit messages, tickets.
- When renaming, rename everywhere in the same change: code, tests, diagrams,
  docs, issue/spec text.

## Scope discipline

Change only what the task names. Architecture, patterns, and interfaces stay
put unless the task says otherwise, and no implied authority to refactor.
Simplification that removes LoC is welcome, but flag WHAT changed and WHY. Root
cause out of scope -> land smallest in-scope fix, report rest open.

## Ambiguity

Task ambiguous, conflicting with existing patterns, or implying architecture
change -> stop. Unattended agent return BLOCKED naming the ambiguity.
