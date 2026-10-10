---
name: principle-skeptically-review
description: "Apply when you review a design sketch or new code as a gate. Assume the work has flaws and look for them. Approve only when the evidence convinces you; fail the review on one substantive objection."
user-invocable: false
---

# Skeptically Review

A review is a gate between the work and the next step. Assume that the work has flaws, and look for them. Approve the work only when the evidence convinces you that it is sound.

**Why:** The author has the same blind spots that made the flaw. A reviewer who starts from "probably fine" finds only what the author already checked. A reviewer who starts from "this has flaws" finds the rest. A design flaw that passes the gate costs a rewrite after the code exists.

**Pattern:**
- Read all of the submission and its done-when before you judge. Do not skim.
- Find the unstated assumptions. Name what must be true for the work to succeed, then find the type, the code, or the test that makes it true.
- Find the failure cases: errors, empty and boundary inputs, retries, partial runs, and concurrent actors.
- Find the over-engineering and the hidden complexity: a layer, an option, or an abstraction that the done-when does not need, or a simpler way that the work ignored.
- Find the scope gaps: a missed requirement, work outside the scope, or a done-when that is too vague to check.
- Find the claims that the artifact does not prove, in a comment, a commit message, or the sketch.

**On a design sketch:** stub bodies are correct. Judge the shape. Check that the types and contracts hold each case in the done-when, that each interface hides its complexity, that the sketch names what it breaks elsewhere, and that the plan is realistic.

**On new code:** check correctness, side effects on callers, and stale assumptions: the comments, docs, and tests that the change made wrong. Review the test code with the same rigor as the production code. A test that passes for the wrong reason is worse than no test.

**Objections:**
- Each objection must be substantive. Name the evidence (a `file:line` or a sketch section) and the case that breaks.
- Raise the problem. Do not write an alternative design.
- Do not approve because of convenience or time pressure. Do not object only to look strict.

**Verdict:** pass or fail. One substantive objection makes the verdict fail. On a fail, list each objection. When the approach itself is unsound, say so, so that the author goes back to the design instead of a patch. On a pass, list the conditions of the approval, if any.

**Later rounds:** first check each objection of the last failed round. An objection that is not fixed stays. Then review all of the work again, because a fix can break something that an earlier round passed.
