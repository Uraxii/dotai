---
name: principle-skeptical-review
description: "Apply when you review a design sketch or a code diff as a gate. Assume it has flaws and look for them, sort each finding into must-fix, should-fix-or-explain, or worth-noting, and fail the review on one must-fix."
user-invocable: false
---

# Skeptical Review

A review is a gate between the work and the next step. Pass the work only when the evidence convinces you that it is sound.

**Why:** The author shares the blind spots that made the flaw. A reviewer who starts from "probably fine" finds what the author already checked. A reviewer who starts from "this has flaws" finds the rest.

Read all of the submission and the done-when before you judge. Do not skim. Then attack it:

- **Unstated assumptions.** Name what must be true for the work to succeed. Find the code, the type, or the test that makes it true.
- **Failure cases.** Errors, empty and boundary inputs, retries, partial runs, and concurrent actors.
- **Over-engineering and hidden complexity.** A layer, an option, or an abstraction that the done-when does not need. A simpler way that the work ignored.
- **Scope.** A missed requirement, work outside the scope, or a done-when too vague to check.
- **Unbacked claims.** A statement in a comment, a commit, or the sketch that the artifact does not prove.

On a design sketch, `not implemented` bodies are correct. Judge the shape. Check that the types and contracts hold each case in the done-when, that each interface hides its complexity, that the sketch names what it breaks elsewhere, and that the plan is realistic.

On a code diff, check correctness, side effects on callers, and stale assumptions: comments, docs, and tests that the change made wrong.

Every objection must be substantive. Name the evidence (a `file:line` or a sketch section) and the case that breaks. Raise the problem. Do not write an alternative design. Do not pass the work because of time pressure, and do not fail it to look strict.

## Tiers

- **Must-fix.** Wrong behavior, a missed requirement, a contract that does not hold, or a claim the artifact does not back.
- **Should-fix-or-explain.** A real weakness. The author fixes it or answers it with a reason.
- **Worth-noting.** Not blocking. The author can ignore it.

One must-fix makes the verdict fail. With no must-fix, the verdict is pass.

In a later round, check each item of the last failed round first. A must-fix that is not fixed stays a must-fix. A should-fix-or-explain item with neither a fix nor an answer, or with an answer you reject, becomes a must-fix. Give the reason you reject the answer. Then review all of the work again, because a fix can break something an earlier round passed.
