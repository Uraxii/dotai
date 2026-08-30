# Opening a PR

Invoked at the end of every other role.

**Worktree.** Work from a git worktree off main; subagents inherit it.
Multiple parallel spawns on the same branch each get their own worktree, or
`git fetch && git reset --hard origin/<branch>` between them. Dirty branch
with unrelated work: patch out, fresh worktree, apply. Snarled worktree: reset
from main, redo minimally.

**Commits.** Commit liberally; rebase into small, ordered commits before
opening PRs. Each commit is a future PR: landable, ordered to tell the story.
Amend when the fix belongs in a just-made commit; new commit when separable.

**PRs.** Apply `unslop` to the diff before commit and to the PR description
and commit bodies. Strip comments per the comment rule in
`principle-code-quality` before review. Small PRs, 5 narrow over 1 fat; stack
follow-ups, branch off main only for genuinely independent work. For stacked
PRs use whatever stacking tool the team uses: small, ordered slices, stack
visible to reviewers. `gh pr view <number>` before referencing PR status.
Rebase on `main` before substantial stack work. No `## Summary` /
`## Test plan` boilerplate on small PRs; commit bodies do not restate the
subject. After opening, run Babysit (`roles/babysit.md`); push back when
feedback drifts. An in-flight review verdict blocks merge exactly as red CI
does; synthesize the interrogate verdict BEFORE merging, never in parallel
with it.

A subagent that opens a PR runs `interrogate` and `unslop`, returns the URL,
and does NOT babysit. Return to the parent.
