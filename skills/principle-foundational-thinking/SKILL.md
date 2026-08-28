---
name: principle-foundational-thinking
description: Use at the very start of a new area, before any logic exists, to fix the core data structure, decide which piece gets built first, and name what two concurrent actors share. Boundary, module interfaces and seams belong to the `codebase-design` skill and the domain vocabulary to the `code-quality` skill.
---

# Foundational thinking

Structural decision protect option value, code-level decision protect
simplicity. Over-engineering often a premature decision closing doors; right
foundational data structure keep doors open.

## Data structures first

Get data shape right BEFORE writing logic. Right shape make downstream code
obvious. Define core types early. Trace every access pattern; pick structure
matching dominant paths. Late data-structure change = rewrite, early = often
one-line diff.

At code level: DRY the structure, not every line, types and data models
converge. Three similar statements still beat premature abstraction. Explicit
over clever. Test behaviour and edge case, not line count.

**Concurrency corollary.** Before sharing state between actors (thread, coroutine, peer, worker process,
CI job) ask: what happen if another actor modify this concurrently? Answer not
"nothing" -> isolate.

## Scaffold first

Helps every later phase -> do it first. CI, lint, test harness, shared types,
headless run script are scaffold. Sequence for option value: setup before
features, tests before fixes. Commits small and single-purpose. Each increment
land a coherent abstraction or deepen one that exist; do not spread a new
capability across callers as special-case coordination. Subtraction come before
scaffolding: remove dead weight first, then lay foundation.
