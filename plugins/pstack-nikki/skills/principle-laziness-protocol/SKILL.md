---
name: principle-laziness-protocol
description: Use when you pick up a brief describing sprawl, layers, or wrappers, or asking for something to be cut back or deleted, and run the `ponytail` skill on it first. This is the deeper treatment the `ponytail` skill escalates to, never a first-pass substitute for it. Use after ponytail has already been applied and the change still grows layers, wrappers, config options, or parameters threaded through many files, or when the fix is to delete existing code rather than to keep one new diff small. Inventories what can be removed outright and re-sequences the work around subtraction.
---

# Laziness protocol

Writing code cheap for model, so over-engineering easy. Borrow human maintainer
fatigue. Most result, least code and complexity.

- **Prefer deletion.** Refactor or improve request -> hunt removals before
  additions.
- **Flat call hierarchy.** Answering one question needs tracing >3 files or
  layers -> flatten. Rich interface hiding real work is NOT deep chain.
- **Consolidate decisions.** Same choice repeated in several places -> one
  source of truth, pass result as simple flag.
- **Minimize diff.** Smallest change solving problem. Fewer lines beat
  "elegant" boilerplate.
- **Question threading.** Task say "pass new flag through types, schema,
  autoload, render graph, pipeline stage" -> stop, find direct path.
- **Sweat small leaks.** Tiny pass-throughs, representation leaks, duplicated
  choices compound into permanent coordination cost.
- **Refuse one-off structure.** Abstraction with one implementation -> inline
  it. Config option nobody asked for -> named constant. Templating layer over a
  file used exactly once -> literal file.

**Prime directive:** human dev would find code exhausting to maintain -> bad
solution. Be lazy. Stay simple.
