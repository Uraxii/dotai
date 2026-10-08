# Beads work loop

A bead holds the state of one delegated unit, from creation to close. This reference names who writes what to the bead and when. It matches bd 1.3.1. `bd help <command>` is the authority on flags.

## Coordinator creates the bead and spawns the worker

1. Create the bead with its done-when and its epic.

   ```sh
   bd create "<title>" --acceptance "<done-when>" --parent <epic>
   ```

2. Record a program decision as a decision bead under the epic, with `bd create "<decision>" -t decision --parent <epic>`. To change a decision, create the new decision bead and run `bd supersede <old> --with <new>`. That command closes the old bead with a pointer to the new one.
3. Create the worktree with `bd worktree create <path> --branch <branch>`. It branches from the main checkout's HEAD, and it adds a path inside the checkout to `.gitignore`, so give a path outside the checkout. If the command fails or the branch needs another base, use `git worktree add <path> -b <branch> <base>`.
4. Spawn the worker with this prompt and nothing else. For an Orchestrate unit, append ` Stop at stage=built.` to it.

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
2. Read the scope with `bd show <id>`.
3. A claim carries a lease that expires 5 minutes after the claim or the last heartbeat. During long work, run `bd heartbeat <id>` more often than that. A heartbeat writes no Dolt commit.
4. End each commit subject with `(<id>)` and put the why in the commit body. `git log --grep '(<id>)'` lists the bead's commits.
5. If your spawn prompt ends with `Stop at stage=built.`, leave the bead open. After your last push, run these commands, then end with a final message that names the branch and the SHA. Clearing the assignee hands the bead back to the coordinator, which closes it after the PR lands.

   ```sh
   bd set-state <id> stage=built --reason "ready at <SHA>"
   bd comment <id> "ready at <SHA> on <branch>"
   bd update <id> --assignee ""
   ```

6. Otherwise, close the bead with `bd close <id> --reason "<what changed, proof, SHA>"`. The final message repeats the reason.

## Reviewer records the verdict

Set `BEADS_ACTOR` to the reviewer's actor name, and set `BD_ACTOR` too if the reviewer commits. Then run `bd comment <id> "verdict <X> at <SHA>"`. The SHA ties the verdict to the commit that was reviewed.

## Recover a dead worker or correct a live one

To replace a dead worker, spawn a fresh worker with the same prompt. It runs under the same actor name, and `bd update <id> --claim` succeeds for the actor that already holds the bead, so the bead needs no reclaim.

If a different actor takes over the bead, first run `bd reclaim --id <id>`. It sets that bead back to open with no assignee, but only if its lease expired more than a grace window ago. The grace window is 10 minutes, twice the lease, and `--older-than <duration>` changes it. A bead with a live lease stays as it is.

Run `bd reclaim` only with `--id`. Without it, the command reverts every stale lease in the store, including the beads of workers that are alive but have not sent a heartbeat.

To correct a live worker, send the correction with `SendMessage`. Otherwise, change the bead with `bd update <id> --description "<text>"` or `--acceptance "<text>"` and respawn. `bd edit` opens an editor and blocks, so do not use it.

## Notes

Notes are facts with evidence: what happened, where, and the proof. Never write 'always', 'never', or 'must'. A closed bead is history, not instructions for new work.

## Proof that claims and closes survive concurrency

The loop depends on two bd behaviors. When several actors claim one bead at once, exactly one wins. When several processes close different beads at once, every close lands.

[`scripts/check_bd_concurrency.py`](../scripts/check_bd_concurrency.py) races both on a throwaway store in a temp dir, 10 rounds each, and exits 1 on the first failure. It needs bd on PATH, so CI does not run it. Rerun it after a bd upgrade.

```sh
python3 scripts/check_bd_concurrency.py
```

Run the command from this skill's directory. Ten rounds take about 2.5 minutes.
