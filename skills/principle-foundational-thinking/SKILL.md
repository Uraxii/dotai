---
name: principle-foundational-thinking
description: Use at the very start of a new area, before any logic exists, to fix the core data structure, decide which piece gets built first, and name what two concurrent actors share. Boundary, module interfaces and seams belong to the `codebase-design` skill and the domain vocabulary to the `code-quality` skill.
---

# Foundational thinking

Structural decision protect option value. Code-level decision protect
simplicity. Over-engineering often a premature decision closing doors. Right
foundational data structure keep doors open.

## Data structures first

Get data shape right BEFORE writing logic. Right shape make downstream code
obvious.

- Define core types early.
- Trace every access pattern; pick structure matching dominant paths.
- Late data-structure change = rewrite. Early = often one-line diff.

Where it bites: Godot node tree shape and resource split decide save/load and
network sync cost later. Art pipeline manifest schema decide whether re-render
is incremental or always full. Infra naming and tag scheme decide whether the
query is possible at all.

## At code level

- DRY the structure, not every line. Types and data models converge.
- Three similar statements still beat premature abstraction.
- Explicit over clever. Test behaviour and edge case, not line count.

## Concurrency corollary

Before sharing state between actors (thread, coroutine, peer, worker process,
CI job) ask: what happen if another actor modify this concurrently? Answer not
"nothing" -> isolate.

## Scaffold first

Helps every later phase -> do it first. Ask: does every subsequent phase
benefit from this existing? CI, lint, test harness, shared types, headless run
script are scaffold. Sequence for option value: setup before features, tests
before fixes. Commits small and single-purpose.

Each increment land a coherent abstraction or deepen one that exist. Do not
spread a new capability across callers as special-case coordination.

Subtraction come before scaffolding: remove dead weight first, then lay
foundation.
