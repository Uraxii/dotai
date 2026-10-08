# Beads work loop

A bead holds the state of one delegated unit, from creation to close. This reference names who writes what to the bead and when. It matches bd 1.3.1. `bd help <command>` is the authority on flags.

## Coordinator creates the bead and spawns the worker

1. Create the bead with its done-when and its epic.

   ```sh
   bd create "<title>" --acceptance "<done-when>" --parent <epic>
   ```

2. Record a program decision as a decision bead under the epic, with `bd create "<decision>" -t decision --parent <epic>`. To change a decision, create the new decision bead and run `bd supersede <old> --with <new>`. That command closes the old bead with a pointer to the new one.
3. Create the worktree, then spawn the worker with this prompt and nothing else.

   ```text
   Claim bead <id> as <actor>. Work in <worktree>.
   ```

   The actor name is `<role>-<bead id>`, for example `developer-dotai-sge.2`.

## Worker claims, commits, and closes

The worker inherits `BEADS_DIR` from the session environment as an absolute path. A linked worktree has no `.claude/settings.local.json`, so the inherited variable is the only way bd finds the store from inside it.

Each shell call starts fresh. Set both actor variables on every call that runs a bd command or `git commit`.

```sh
export BEADS_ACTOR=<actor> BD_ACTOR=<actor>
```

bd records claims and history under `BEADS_ACTOR`. The beads `prepare-commit-msg` hook reads only `BD_ACTOR` and appends `Executed-By: <actor>` to the commit message. A commit made without `BD_ACTOR` gets no trailer.

1. Claim the bead with `bd update <id> --claim`. If another actor holds it, the claim exits 1 and changes nothing. Stop and report the holder.
2. A claim carries a lease that expires 5 minutes after the claim or the last heartbeat. During long work, run `bd heartbeat <id>` more often than that. A heartbeat writes no Dolt commit.
3. End each commit subject with `(<id>)` and put the why in the commit body. `git log --grep '(<id>)'` lists the bead's commits.
4. Close the bead with `bd close <id> --reason "<what changed, proof, SHA>"`. The final message repeats the reason.

## Reviewer records the verdict

Run `bd comment <id> "verdict <X> at <SHA>"`. The SHA ties the verdict to the commit that was reviewed.

## Recover a dead worker or correct a live one

A dead worker stops heartbeating, and its lease expires. Nothing reverts the bead on its own. Run `bd reclaim --older-than <ttl>` to set every bead whose lease expired more than `<ttl>` ago back to open with no assignee. Without the flag, `<ttl>` is 10 minutes, twice the lease. Then spawn a fresh worker with the same prompt.

To correct a live worker, send the correction with `SendMessage`. Otherwise, change the bead with `bd update <id> --description "<text>"` or `--acceptance "<text>"` and respawn. `bd edit` opens an editor and blocks, so do not use it.

## Notes

Notes are facts with evidence: what happened, where, and the proof. Never write 'always', 'never', or 'must'. A closed bead is history, not instructions for new work.

## Proof that claims and closes survive concurrency

The loop depends on two bd behaviors. When several actors claim one bead at once, exactly one wins. When several processes close different beads at once, every close lands. bd 1.1 in embedded mode lost 7 of 8 concurrent closes (beads issue #4767).

[`scripts/check_bd_concurrency.py`](../scripts/check_bd_concurrency.py) races both on a throwaway store in a temp dir, 10 rounds each, and exits 1 on the first failure. It needs bd on PATH, so CI does not run it. Rerun it after a bd upgrade.

```sh
python3 scripts/check_bd_concurrency.py
```

Run the command from this skill's directory. Ten rounds take about 2.5 minutes.
