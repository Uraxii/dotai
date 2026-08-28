# Visual parity

Pick when: "make X match Y exactly", styling-system migrations, porting a UI
across frameworks. You own pixel-exact equivalence. The baseline is the spec;
you do not touch it. Equivalence is verified by image diff, not by eye.

1. Establish the baseline first, before any migration: a visual regression
   harness screenshotting the current component across its states, plus the
   target when matching two implementations. No baseline, no parity claim. A
   blocking prerequisite, not a follow-up.
2. Anti-shortcut clauses, stated and held: no harness edits, no baseline
   tampering, no restructuring to make a diff pass. Baseline looks wrong ->
   stop and ask, do not edit it.
3. Migrate one component at a time. Independent artifacts, so parallelize
   across worktrees, one owner per component
   (`principle-code-quality`). Shared primitives migrate first as a blocking
   phase.
4. Verify each component against its baseline by image diff on the matching
   surface. A nonzero diff is a fail; investigate the pixel delta, do not wave
   it through. Iterate per component until the diff is zero, on a recurring
   run if the harness has one.
5. Run Opening a PR (`roles/opening-a-pr.md`) per component or per safe batch.

**Reply:** components migrated, the diff for each, the baseline harness
location, what is left.
