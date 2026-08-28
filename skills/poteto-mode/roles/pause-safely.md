# Pause safely

Pick when: "pause safely", "I need to go offline", "restart",
"board my flight", and when context is about to compact or summarize. You own
a clean stop. Leave a checkpoint a cold-start agent can resume from.

Explicit only. On "keep going", "going to bed, keep going", or "do not stop",
do not pause. Those mean continue, and Autonomous run already checkpoints per
iteration.

1. Stop at a safe boundary. Finish the current atomic step or back out of it.
   Never stop mid-edit in a known-broken state. Start nothing new; cancel any
   nested subagents.
2. Do not cross an irreversible line to pause. No PR and no push unless you
   already had one out.
3. Make the work durable. Commit uncommitted edits as one clear `wip:` commit
   on the current branch so nothing is lost. Tree broken -> say so in the
   commit body in one line.
4. Write the resume note off-context via `handoff`: intent, what you were
   doing, progress and what is verified, current state, next steps, key files,
   gotchas. For the compaction trigger write it to a file, because the
   in-context plan will not survive summarization. A `show-me-your-work` trail
   exists -> point at it instead of duplicating it.

**Reply:** where you are in the loop, what is on disk versus still in your head
(paths, no diff dumps), the commits you made and whether the tree is clean,
and the first action on resume. This is a pause, not a final report. Resume is
Session pickup (`roles/session-pickup.md`) reading this note.
