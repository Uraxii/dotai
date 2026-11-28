---
shape: router
---

# <Topic> playbooks

You own <topic> requests. Pick one route, read its file, and follow it.

- "<user words for a risky change>": read [ordered-irreversible](ordered-irreversible.md).
- "<user words for a defect>": read [diagnose-loop](diagnose-loop.md).
  Not for a new feature; see build-and-verify.
- "<user words for a new feature>": read [build-and-verify](build-and-verify.md).
- "<user words for a question>": read [read-only-answer](read-only-answer.md).
- "<user words for run until done>": read [run-to-predicate](run-to-predicate.md).

When two routes match, the route higher in this list wins.

Default: for a request that matches no route, ask which outcome the user
wants. Do not guess a route.
