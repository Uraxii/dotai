# Trace forensics

Pick when: a dropped `.cpuprofile`, `Trace-*.json.gz`, `Spindump.txt`, or
`.heapsnapshot` paired with "why is this slow / unresponsive / leaking /
crashing". You own the diagnosis from the artifact. Load it, shape it, narrow
to the cause, attribute to source.

Distinct from Runtime forensics (`roles/runtime-forensics.md`), which
instruments the live process. Here the capture already exists; the artifact is
a fixed dataset: read it, do not re-run it. Keep tooling generic: a
DevTools or trace parser for cpuprofile and `.json.gz`, a text editor for a
spindump, your heap tooling for a heapsnapshot.

1. Identify the format and load it with the right tool. Parse large artifacts
   in a subagent (`principle-guard-the-context-window`); keep the reduced
   finding in the main thread.
2. Transform the raw artifact into a form you can query. Dump the trace or
   heap snapshot into sqlite, one row per sample, frame, or node. Reach a
   queryable shape first.
3. Narrow to the cause. Query for the frames holding most time and walk
   the call tree to the hot path. Leak -> follow the retainer chain from the
   leaked object to a GC root. Spindump -> find the thread stuck on-CPU or
   blocked and its wait reason.
4. Attribute to source. Map the hot frame to file, symbol, and line via the
   artifact's own symbols. A frame with no source mapping is not yet a
   diagnosis; resolve the symbols, or say plainly the artifact does not carry
   them.
5. Confirm against a paired capture when you have one. Diff a before and after
   artifact so the attribution is the real regression, not background noise.
   Without one, mark the finding as the strongest hypothesis the artifact
   supports, not a confirmed cause.
6. Hand back a cited diagnosis; no fix unless asked. Route to Bug fix or Perf
   issue once the cause is known. Throughput checkpoint stays one line:
   `throughput checkpoint: n/a, read-only forensics`.

**Reply:** the artifact and format, the reduced finding, the source location,
artifact paths, and whether a paired capture confirmed it.
