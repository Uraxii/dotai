---
name: code-quality
description: Load before writing or changing code in any language, and before reviewing a diff, designing types or interfaces, refactoring, or debugging. Covers cross-language limits, naming, code smells, type and boundary discipline, domain modelling, reader load, deletion-first sequencing, and scope rules, plus on-demand references for Python, TypeScript, C#, GDScript, and Godot.
---

# Code quality (all languages, all vendors)

Repo's own documented standard override this file. Skip anything the repo's
tooling already enforce. Working in one of these languages, read the matching
file on demand: `references/python.md`, `references/typescript.md`,
`references/csharp.md`, `references/gdscript.md`, `references/godot.md`. Read
adjacent code first: match its naming, formatting, error handling, logging,
config, test patterns, and use the utilities already there.

## Hard limits

- Function <=40 LoC. File <=600 LoC, one cohesive responsibility.
- Line <=80 chars (<=100 when readability win).
- Explicit return types. Function contracts stated.
- No bare catch/except. Handle errors explicit, per surrounding context.
- No magic numbers. Named constants carry domain + units.
- Guard clauses over deep nesting. Nesting >3 -> extract function.
- Compute or mutate, never both in same function.
- YAGNI. No dependency added without explicit approval.

## Types and boundaries

Type checker is proof assistant; defining errors out of existence beats adding
handlers.

- Illegal states unrepresentable: sum type over bag of optionals. Comment
  needed to say which field combo valid -> type too loose.
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
  loose booleans, typed object over loose params, map/registry/discriminated
  union over branching spread across files, reducer or event model over ad-hoc
  mutation, queue/cache/index/tree when access pattern ask it.
- Module own one body of domain knowledge. Execution order is not ownership:
  load/validate/transform/save modules repeat same rules per step.
- Tell you skipped it: new feature grow if/else chain by one branch, or second
  boolean must stay in sync with first.

## Reader load

- Guard two axes: layers to trace, state held in reader's head. Collapse layer
  not earning keep: one-caller wrapper, adapter with no second implementation,
  pass-through repeating same methods and args. Adjacent layers must change
  abstraction; broad interface hiding little complexity teach reader nothing.
- Shrink state scope: pure function > local > field > module state > global.
  Derive instead of sync. Name invariant once at boundary, not per consumer.
- Test: new reader answer "where X come from?" and "what can change X?" in
  under 30 seconds. No -> cut layers or cut state.

**Comments.** Comment restating code, narrating change, or apologizing for a
workaround: delete, fix the code instead. Constraint comment ("do not remove",
"ask X first") is an unenforced rule: encode as type, runtime check, test, or
lint, then delete it. Suppression is a comment too; correctness or safety
suppression must die, not be silenced. Keep only comment about thing we cannot
change.

## Subtract first

- Remove before construct, cut before polish. Leave design simpler behind same
  or smaller surface than found.
- Design for observed usage. No speculative validator, parser, guard beyond
  spec; out-of-spec feature drag guards behind it.
- New internal API: inventory callers, migrate, delete old API same wave. No
  compatibility layer for internal callers, temporary adapter time-boxed. Move
  tests to new contract, delete tests pinning old impl detail.

## Shared state and repeatability

- Concurrent writers: eliminate sharing first, each actor own its file, key,
  branch, dir, merged at read boundary. Sharing truly invariant -> serialize
  structurally (lockfile, sequential phase, single-writer owner, atomic
  compare-and-swap). Convention is not concurrency control.
- State-mutating op must converge: same end state run twice, or after crash at
  any point. Scan state, clean stale artifact, adopt live session, PID-based
  stale lock. "Depends what was left behind" -> add reconciliation step.

**Debugging.** Loop lives in the `diagnose` skill. Two rules it does not
carry: fix pattern not instance (grep the shape, fix all of them), and "broke
after restart" -> suspect stale persistent state first, code not change between
runs, state do.

## Sequencing work

- Smallest units each ending in checkable state, verified before next, never
  batched then verified once. Rebase onto clean trunk first.
- Order commits so sequence prove itself: failing test then fix, subtraction
  then reshape, scaffold then feature. Each unit land on its own.
- Non-trivial repeated work -> `principle-build-the-lever`, not hand edits.

## Smell baseline (Fowler, _Refactoring_ ch.3)

Labelled heuristic, never hard violation. Rest of catalogue covered above:

- **Duplicated Code**: same logic shape in two places -> extract, call both.
- **Feature Envy**: method reach another object's data more than own -> move
  method onto data it envy.
- **Shotgun Surgery**: one logical change force scattered edits -> gather what
  changes together.
- **Message Chains**: long `a.b().c().d()` -> hide walk behind one method.
- **Refused Bequest**: subclass ignore most of inheritance -> composition.

## Code naming (engineering artifacts, all languages)

Name must reveal purpose to reader with no other context.

- Name the thing and its effect, not the mechanism or metaphor. `projectile`
  not `controller entity`. `change_owner` not `grant_control`.
- No scheduling word as identity: Deferred, Pending, Delayed, Async, Lazy say
  WHEN code run, never what thing IS.
- No structure filler as identity: Manager, Controller, Handler, Helper, Util,
  Service, Data, Info, Object, Item. (Service only under an established
  subsystem convention, and the prefix must still carry meaning.)
- Plain domain word (projectile, hitbox, cooldown) over invented jargon.
- Constants and fields carry domain + units: `REVIVE_TIME_SEC` not
  `TIME_EPSILON`. `cooldown_remaining` not `timer`.
- Applies everywhere a human read: code, tests, diagrams, spec text, commit
  messages, tickets. Rename everywhere in the same change.

## Scope discipline

Change only what the task names. Architecture, patterns, interfaces stay put
unless the task say otherwise. Simplification removing LoC welcome, but flag
WHAT changed and WHY. Root cause out of scope -> land smallest in-scope fix,
report rest open. Task ambiguous or implying architecture change -> stop,
report BLOCKED naming the ambiguity.
