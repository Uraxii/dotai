# Spawn brief

Every field, every spawn. One-command task collapse to a paragraph still naming goal, scope, verify command, report shape.

```text
GOAL         one sentence outcome, executable by stranger with no chat access
SCOPE        paths this task may write; paths it may not; its branch
SKILLS       active role first (e.g. prototype) with its mode line copied
             verbatim, then skills by name; agents carry no defaults
CONTEXT      file paths and issue ids; upstream reports pasted in full when
             this task depends on them (agents cannot see siblings)
ACCEPTANCE   checkable criteria, one per line
VERIFY       exact commands to run, plus known gotchas
TIMEBOX      rough runtime cap; on expiry return partial findings and stop
FORBIDDEN    out-of-scope edits, task-specific bans, read-only or no-pixels
REPORT       status, branch, head SHA, verdict, what was actually run,
             deviations, suggested follow-ups
```

Read-only means FORBIDDEN says "no writes, no commits, inspection commands only". No-pixels means FORBIDDEN says "never load image pixels, hold paths and verdict text only".

GOAL and ACCEPTANCE state outcomes. A brief that prescribes the fix's SHAPE must cite the command that proved the shape works; otherwise label the shape HYPOTHESIS, so the agent knows measurement overrides it.

Work ordered by the user -> GOAL quotes the ordering sentence verbatim. No quote to back it = your inference, not their order; confirm before commissioning a workstream on it.

Child briefs narrow, never widen. An orchestrator copies its own FORBIDDEN verbatim into every child and may only add lines; child SCOPE is a subset of its own. A child authorized to write what its parent may not touch is a contradiction: resolve it before spawning, not after the write.
