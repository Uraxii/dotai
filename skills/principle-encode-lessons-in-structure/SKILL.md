---
name: principle-encode-lessons-in-structure
description: Recurrence is the trigger. Use on the SECOND occurrence of a lesson, when the human corrects the same thing twice, when about to write an instruction already written elsewhere, or when a class of bug returns after being fixed one instance at a time. Never fires on a first-time rule or on any single comment. Converts the repeated correction into a mechanism (type, lint rule, CI check, canonical helper, runtime assert, script) and deletes the prose.
---

# Encode lessons in structure

Recurring fix belong in mechanism, not in more text. Text instruction easy to
miss: need reader notice, remember, comply. Mechanism enforce without
cooperation.

## Pattern

Catch self writing same instruction second time:

1. Ask: type, lint rule, CI check, helper, runtime assert, or script?
2. Yes -> encode it, delete the instruction.
3. No, real judgement -> make instruction prominent, add failure-mode example.

## Pick strongest rung

Strongest the situation allow, best first: unrepresentable state (type or
schema make bad value impossible) > fails CI (lint, banned symbol, schema
validation, import test) > canonical helper (wrong path stop existing) >
runtime assert at boundary > prose, last resort. Agents copy whatever
surrounding code already do, so weaker guard become next template. Fix is
structural -> use ONLY the structural fix. The instruction IS the symptom.

## Anti-patterns

- Acknowledge without recording. "I will keep that in mind" does not persist.
- Record without routing. Note about a lint rule that should exist is wasted
  until the rule exist.
- Fix without generalising. One instance patched, pattern left alive.

## Procedure

Lesson from the session just finished, or the human corrected the same thing
twice in a transcript -> run `reflect`. It reviews the transcript and routes
each learning to an edit on an existing skill, the strongest rung that fits.
A skill edit is the mechanism for agents; a type, lint, or CI rule is the
mechanism for code.
