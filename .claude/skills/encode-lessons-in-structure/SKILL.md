---
name: encode-lessons-in-structure
description: Recurrence is the trigger. Use on the SECOND occurrence of a lesson, when the human corrects the same thing twice, when about to write an instruction already written elsewhere, or when a class of bug returns after being fixed one instance at a time. Never fires on a first-time rule or on any single comment. Converts the repeated correction into a mechanism (type, lint rule, CI check, canonical helper, runtime assert, script) and deletes the prose.
---

# Encode Lessons in Structure

Recurring fix belong in mechanism, not in more text. Every error, human
correction, surprising outcome is learning signal. Capture, route, close loop.

**Why:** text instruction easy to miss. Needs reader to notice, remember,
comply. Mechanism enforce without cooperation.

## Pattern

Catch self writing same instruction second time:

1. Ask: type, lint rule, CI check, helper, runtime assert, or script?
2. Yes -> encode it, delete the instruction.
3. No, real judgement -> make instruction prominent, add failure-mode example.

## Pick strongest rung

Strongest the situation allow, in order:

1. **Unrepresentable state.** Type, enum, or resource schema make bad value
   impossible.
2. **Fails CI.** Lint rule, banned symbol, schema validation, import test.
3. **Canonical helper.** One function everyone call; wrong path stop existing.
4. **Runtime assert.** Loud failure at boundary.
5. **Prose.** Last resort only.

Weaker guard become next template, because agents copy whatever surrounding
code already do.

## Domain shapes

- Godot: "forgot to free node" -> assert in `_exit_tree`. Repeated magic path
  string -> preloaded const.
- Art pipeline: "always set seed" -> default in workflow loader, not a note.
- Infra: "always tag resource" -> policy check in CI, not README line.

**Corollary:** do not paper over symptom. Fix is structural -> use ONLY the
structural fix. The instruction IS the symptom.

## Anti-patterns

- Acknowledge without recording. "I will keep that in mind" does not persist.
- Record without routing. Note about a lint rule that should exist is wasted
  until the rule exist.
- Fix without generalising. One instance patched, pattern left alive.
