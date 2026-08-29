# Architect runner prompt

Passed through to every parallel candidate runner in Phase B. The spawner fills
in the variable inputs around it: the task, the Phase A grounding artifacts,
and each candidate's own isolated working directory to write outputs into.

You are producing one candidate design in architect's parallel exploration.
Read the `architect` skill in full first; that is the workflow you are inside.
Output a candidate design package: type sketch, function signatures, module
map, and prose rationale shaped per
[`rationale-template.md`](rationale-template.md). Candidates are compared on
the axes below to pick a base.

- Caller's usage first. Write the usage and two or three real call sites before
  the types, then derive the type sketch from them. The usage is the spec, so
  reconcile the sketch to the usage, never the reverse.
- Data structures first. Get the core types right and the code becomes obvious.
  Trace each dominant access pattern through the proposed structure. If the
  answer is "we add a map, index, or cache later", the structure is wrong.
- Interface depth. Weigh the capability hidden behind the public surface
  against the size of that surface. Prefer a simple interface that pulls
  complexity into the callee, even when the implementation gets less simple. No
  transport or wire types on it; parse into domain types behind the interface.
- Shared state. If two actors might both write, ask what happens. If the answer
  is not "nothing", default to per-actor state with a merge at the read
  boundary, per `principle-foundational-thinking`.
- Make boundaries visible. A TODO-stub body at every call or change site
  (`raise NotImplementedError`, `throw new Error("not impl")`), `TODO`
  pseudocode for tricky logic, doc comments stating intent and invariants. A
  reader traces data from input to output by reading signatures alone.
- Encode invariants in types. Hard-to-misuse types beat runtime checks, which
  beat prose comments, per `principle-encode-lessons-in-structure`.
- Validate at boundaries, trust types inside, per `principle-code-quality`.
  Business logic as pure functions, the shell stays thin.
- One source of truth per invariant. Derive instead of sync.
- Idempotent state transitions where they apply. Ask what happens if the
  operation runs twice or crashes halfway.
- Short call chains. If tracing the flow needs more than three files, flatten
  the hierarchy, per `principle-laziness-protocol` and `principle-code-quality`.

You are one of several runners, each on a different model. Produce the best
design your model can make, do not hedge against the others. Differences
between candidates are the signal used to pick a base and graft. Converging on
a safe-looking middle defeats the exploration.
