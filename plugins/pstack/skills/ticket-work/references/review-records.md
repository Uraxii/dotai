# Run a skeptic review

This reference executes one assignment with the prompt `Review bead <gate> at <SHA> in <worktree>.`
The selected playbook chooses when the review starts.

1. Set `BEADS_ACTOR=skeptic-<gate>` on each `bd` call.
   Create and claim your own run bead per [Run records](run-records.md#the-run-bead).
   Do not claim the writer's bead or the gate. Edit no file in the worktree and commit nothing.
2. Read the base, scope, and done-when with `bd show <gate>`.
   Read earlier rounds with `bd comments <gate>`.
   The last failed review is the most recent `verdict fail at <SHA>` comment.
   For a linked test gate, read its description and comments too.
   Read the latest `tests fail at <SHA>` findings and the writer's answers.
3. Review `git diff <base>..<SHA>` in the worktree.
   For a sketch, also read its rationale.
   Judge the work with [principle-skeptical-review](../../principle-skeptical-review/SKILL.md).
   If a last failed round exists at `<old SHA>`, first read `git diff <old SHA>..<SHA>` for the fixes.
4. Assess each linked test finding and answer against the done-when and the preserved tester assertions.
   Resolve each disputed contract before a pass. Edit no tests.
   Write the verdict to a file outside the worktree.
   Its first line is `verdict pass at <SHA>` or `verdict fail at <SHA>`.
   List findings under must-fix, should-fix-or-explain, and worth-noting.
   Mark each item from the last failed review and linked test failure `fixed`, `answered: <reason>`, or `still open`.
   Add the file with `bd comment <gate> --file <file>`.

Close your own step and run beads before return, per Run records. The owner closes the gate.
