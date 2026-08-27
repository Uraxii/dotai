---
name: laziness-protocol
description: The deeper treatment the `ponytail` skill escalates to, never a first-pass substitute for it. Use after ponytail has already been applied and the change still grows layers, wrappers, config options, or parameters threaded through many files, or when the fix is to delete existing code rather than to keep one new diff small. Inventories what can be removed outright and re-sequences the work around subtraction.
---

# Laziness protocol

Writing code cheap for model, so over-engineering easy. Borrow human
maintainer fatigue. Most result, least code and complexity.

## Rules

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

## Shapes to refuse

- Godot: new autoload plus signal bus hop to carry one bool -> read node
  property direct, or export var.
- Art pipeline: wrapper class over workflow JSON -> set dict key.
- Infra: templating layer over compose/module used exactly once -> literal
  file.
- General: config option nobody asked for -> named constant.
- Any: abstraction with one implementation -> inline it.

**Prime directive:** human dev would find code exhausting to maintain -> bad
solution. Be lazy. Stay simple.
