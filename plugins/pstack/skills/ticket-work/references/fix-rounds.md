# Fix a failed round

This reference executes an assignment with `Fix bead <gate> at <SHA> in <worktree>.` in its prompt.

1. Read the review and test comments for the current head with `bd comments <gate>`.
   Read the gate description for related gate IDs.
2. Fix each must-fix item and each failing test in the responsible code.
   Preserve tester-committed tests.
   If a tester test has a wrong contract, explain why in a comment. Leave the test for the fresh reviewer.
3. Fix each should-fix-or-explain item, or answer it with a comment on the gate.
   Use `bd comment <gate> --file <file>` with the line `answered: <item>: <reason>`.
4. Commit and return the new head SHA to the owner.
