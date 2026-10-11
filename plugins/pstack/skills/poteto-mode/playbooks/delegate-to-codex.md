# Delegate to Codex

Start one scoped Codex implementation or native review, then check its outcome against the bead and Git.
The watcher adapter currently applies to Claude Code.
Its runtime procedure is in the [codex-watcher skill](../../codex-watcher/SKILL.md).
Use the [beads work loop](../references/beads-work-loop.md) for the existing gates.

## Prepare the unit

1. Select one implementation unit or one review gate.
   Keep orchestration, search, and tester work with their existing roles.
   If Codex is already unavailable, start a fresh fallback worker under the existing role routing.

2. Create a bead with its scope and acceptance criteria.
   Use a linked worktree for a writer.
   Set an absolute `BEADS_DIR` before you start the watcher.
   Use `developer-<id>` as the writer actor so a fallback can hold the same claim.

3. Send one complete request to the adapter.

   ```text
   Claim bead <id> as developer-<id>. Work in <worktree>.
   Claim bead <id> as developer-<id>. Work in <worktree>. Stop at stage=built.
   Review bead <id> at <SHA> in <worktree>.
   ```

   Append ` Grant: <absolute path> <absolute path>` only for required extra paths.
   Each path must exist and contain no spaces.
   A writer uses the first Codex model in the `feature, refactoring` row of `models.json`.
   A reviewer uses the first Codex model in the `judgment and prose` row.
   The builder reads that file from its own plugin tree.

## Check the result

4. Wait for completion, then read the bead and run records.
   Watcher completion means that the process ended.
   It does not prove that the unit passed.
   The run directory is `${XDG_STATE_HOME:-~/.local/state}/pstack/codex-runs/<id>/<writer|reviewer>/`.
   It holds `prompt.md`, `run.sh`, `codex.jsonl`, and `codex.stderr`.
   A writer also has `last-message.md`.
   A refusal has `refused.txt` when the builder could identify the bead and write the record.

   - A closed bead must have a reason with the result, checks, and SHA.
   - A built bead stays open with `stage:built` and a `ready at <SHA> on <branch>` comment.
   - A review has a `verdict pass at <SHA>` or `verdict fail at <SHA>` comment.
   - A `codex could not finish` comment reports an incomplete run.
   - A refusal record reports why no run started.
   - A claimed bead without an outcome needs inspection of the logs and the exit marker.

5. Verify the reported SHA, branch, diff, and clean status with Git.
   If the scope forbids commits, confirm that HEAD and the worktree remain unchanged.
   If the scope says `Do not push`, verify the local result without a remote equality requirement.
   Otherwise, verify remote equality when the outcome requires a push.
   Scope and notes control all commit and push steps.

   Writers receive the linked Git directory, shared objects, refs, logs, and bead-store parent as narrow write grants.
   They also receive network access and `agents.enabled=false`.
   The shared config and effective hooks remain protected.
   Worktree config is permitted.
   Native review is read-only and receives no extra write grant.
   Its outer process loads bead context and posts the verdict.

   Before Git runs outside the sandbox, inspect the worktree's `.git` pointer and the scoped diff.
   Use `-c core.hooksPath=/dev/null -c core.fsmonitor=false` for each such Git command.
   A writer can modify shared refs and its own worktree config.

## Handle an incomplete run

6. Record the failure on the bead with its command, error, and run directory.
   Report the failure even when a fallback later succeeds.
   Confirm that no Codex process still holds the worktree before a fallback starts.
   Start a fresh worker through the existing role routing with the same scope and actor.
   The worker reads the bead and current worktree before it continues.
   The watcher never performs fallback work.

7. Apply the existing review and tester gates from the beads work loop.
   Use a fresh reviewer after a writer result.
   Stop after the third failed round as that loop requires.
   Report the result with the bead outcome and the Git evidence.
