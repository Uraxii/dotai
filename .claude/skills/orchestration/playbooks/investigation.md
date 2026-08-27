# Investigation

Pick when: read-only question. How X works, why Y was built that way, whether
Z is true, which of two options to pick. Deliverable is cited answer, not diff.

Copy these steps into todolist verbatim before any task-specific todo.

1. **Answer, not a diff.** Nothing gets edited on this task. Answer implying a
   change -> name follow-up, do not make it. Hand back and re-route to Bug fix
   or Feature.
2. **Pin the question.** Restate in one sentence, name what evidence would
   settle it. Cannot state that -> ask user before reading.
3. **Fan out the reading.** Broad sweeps go to `Explore` agents, one question
   each, several parallel. They return conclusions and paths. Load
   `guard-the-context-window`: file dumps stay out of main thread, synthesis
   stays with you.
4. **Evidence over memory.** Every claim carries `path:line` or quoted real
   output you actually ran. Recall is hypothesis, not finding.
5. **Web sources.** Worker loads `capture-source`. Cite stored source, never
   bare link.
6. **Mark the seams.** Split answer into verified and inferred. Label
   inferences as inferences. Could not determine X -> say exactly that.
   Plausible guess in the gap is the failure mode here.
7. **Draw it if structural.** Flow, layering, call path -> `excalidraw-diagrams`.
   One diagram, not a gallery.
8. **Record what gets acted on.** Decision, settled fact, or answer used later
   -> `agent-workbench` kb. Throwaway lookups not stored.

No gate: nothing ships. `unslop` the reply.

**Reply:** answer in one sentence, then evidence as `path:line` lines, what
was verified vs inferred, what could not be determined, follow-up change if
the answer implies one. Decision between options -> tradeoff table plus real
judgment; push back when premise is wrong.
