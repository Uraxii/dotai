# Investigation

Pick when: read-only question. "How does X work?", "why was Y built this
way?", "are we sure about Z?", "should we do X or Y?". Output is a cited
explanation or a recommendation, never a code change. You own the answer.

1. Route through `how` (Explain mode for narrow questions, Critique mode for
   "are we sure?"). Motivation question -> also route through `why`.
2. Throughput checkpoint stays one line:
   `throughput checkpoint: n/a, read-only investigation`. The four-item
   version is for code-shaped work.
3. Produce the `how`-shaped output (Overview / Key Concepts / How It Works /
   Where Things Live / Gotchas), or a recommendation with a tradeoffs table if
   the request is a decision between alternatives.
4. Apply `unslop` to the reply.

No PR, no babysit, no `architect` unless the investigation precedes a
code change. If it does, hand back and re-route to Bug fix or Feature.

**Reply:** the investigation output. For "are we sure?", include real
judgment with reasons. Push back if the premise is wrong.
