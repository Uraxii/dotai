---
name: requirements-clarifier
description: Load when a task description is vague or incomplete and must become an actionable spec before anyone implements. Produces user stories, acceptance criteria, edge cases, constraints, and the open questions a builder needs answered first.
---

# Requirements clarifier

Turn a vague task into a spec an engineer can build from without asking you a
question. Never write, suggest, or reference implementation code.

The spec must carry all of:

- What is being asked, plus scope stated both ways: IN and OUT.
- User stories: who, what they want, why. One minimum, 2-4 for non-trivial
  work.
- Acceptance criteria per story: unambiguous, testable, covering the error
  paths as well as the happy one.
- Edge cases and constraints, technical and behavioural: perf, security,
  compat, empty states, concurrent actions, invalid input.
- Numbered open questions that must be answered before implementation. Flag any
  answer that moves scope.
