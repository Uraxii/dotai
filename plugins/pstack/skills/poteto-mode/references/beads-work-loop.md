# Beads work loop

A bead holds the state of one delegated unit, from creation to close. This reference names who writes what to the bead and when. It matches bd 1.3.1. `bd help <command>` is the authority on flags.

## Beads plugin

pstack requires the beads plugin. Run these operations with your harness's beads skill; the `bd` forms in pstack files define the exact behavior. An agent with only a shell, such as Codex inside its sandbox, runs the `bd` form directly.

## Coordinator creates the bead and spawns the worker

1. Create the bead with its done-when and its epic.

   ```sh
   bd create "<title>" --acceptance "<done-when>" --parent <epic>
   ```

2. Record a program decision as a decision bead under the epic (`bd create "<decision>" -t decision --parent <epic>`). To change a decision, create the new decision bead and supersede the old one with it (`bd supersede <old> --with <new>`). The supersede closes the old bead with a pointer to the new one.
3. Create the worktree (`bd worktree create <path> --branch <branch>`). It branches from the main checkout's HEAD, and it adds a path inside the checkout to `.gitignore`, so give a path outside the checkout. If the command fails or the branch needs another base, use `git worktree add <path> -b <branch> <base>`.
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

bd records claims and history under `BEADS_ACTOR`. The beads `prepare-commit-msg` hook reads only `BD_ACTOR`. It appends `Executed-By: <actor>` after a blank line, which splits the trailer block, unless the message already has an `Executed-By:` trailer. Every commit therefore writes both trailers with `git commit --trailer`, so they form one block and the hook skips.

1. Claim the bead (`bd update <id> --claim`). If another actor holds it, the claim exits 1 and changes nothing. Stop and report the holder.
2. Read the scope (`bd show <id>`), including its NOTES section. A reopened bead holds the reason for the reopen there.
3. A claim carries a lease that expires 5 minutes after the claim or the last heartbeat. During long work, send a heartbeat (`bd heartbeat <id>`) more often than that. A heartbeat writes no Dolt commit.
4. End each commit subject with `(<id>)` and put the why in the commit body. `git log --grep '(<id>)'` lists the bead's commits. Commit with this form, which fails when `BD_ACTOR` is unset, and put no trailer in the `-m` text:

   ```sh
   git commit -m "<subject> (<id>)" -m "<why>" --trailer "Co-Authored-By: <attribution>" --trailer "Executed-By: ${BD_ACTOR:?}"
   ```

   `git interpret-trailers --parse` on the resulting message lists both trailers.
5. If your spawn prompt ends with `Stop at stage=built.`, leave the bead open. Push the branch (`git push origin HEAD`; a Codex sandbox cannot write the repository config, so leave out `-u`). Then run these, then end with a final message that names the branch and the SHA. Clearing the assignee hands the bead back to the coordinator, which closes it after the PR lands.

   - Set the stage label (`bd set-state <id> stage=built --reason "ready at <SHA>"`).
   - Add a comment naming the SHA and branch (`bd comment <id> "ready at <SHA> on <branch>"`).
   - Clear the assignee (`bd update <id> --assignee ""`).

6. Otherwise, close the bead with a reason that says what changed, the proof, and the SHA. The final message repeats the reason. Write the reason to a file, per Text with quotes or several lines.

   ```sh
   bd close <id> --reason-file <file>
   ```

## Text with quotes or several lines

The shell runs backticks and `$(...)` inside double quotes, and a quote in the text ends the string early. Put multi-line text, or text that holds a quote, a backtick, or `$(...)`, in a file and pass the file. Write the file with the Write tool or a quoted heredoc (`<<'EOF'`).

| Text | Command |
| --- | --- |
| Close reason | `bd close <id> --reason-file <file>` |
| Comment | `bd comment <id> --file <file>` |
| Description | `bd update <id> --body-file <file>` |

Use `-` in place of `<file>` to read the text from stdin. `bd comment` takes `--stdin` for the same purpose. Short text with no quote, backtick, or `$` can stay inline.

## Reviewer records the verdict

Set `BEADS_ACTOR` to the reviewer's actor name, and set `BD_ACTOR` too if the reviewer commits. Then record `verdict <X> at <SHA>` as a comment (`bd comment <id> "verdict <X> at <SHA>"`). The SHA ties the verdict to the commit that was reviewed.

## Reopen a closed bead

In bd 1.3.1, the reason given to `bd reopen <id> --reason <text>` does not show in `bd show`, `bd show --json`, or `bd comments`. The next worker never sees it. Put the reason in the bead notes before you reopen (`bd update <id> --append-notes "<reason>"`), then reopen the bead (`bd reopen <id>`). Use `--append-notes`, because `--notes` replaces the existing notes.

## Recover a dead worker or correct a live one

To replace a dead worker, spawn a fresh worker with the same prompt. It runs under the same actor name, and `bd update <id> --claim` succeeds for the actor that already holds the bead, so the bead needs no reclaim.

If a different actor takes over the bead, first reclaim the bead (`bd reclaim --id <id>`). It sets that bead back to open with no assignee, but only if its lease expired more than a grace window ago. The grace window is 10 minutes, twice the lease, and `--older-than <duration>` changes it. A bead with a live lease stays as it is.

Reclaim a stale lease (`bd reclaim`) only with `--id`. Without it, the command reverts every stale lease in the store, including the beads of workers that are alive but have not sent a heartbeat.

To correct a live worker, send the correction with `SendMessage`. Otherwise, change the bead (`bd update <id> --description "<text>"` or `--acceptance "<text>"`) and respawn. `bd edit` opens an editor and blocks, so do not use it.

## Notes

Notes are facts with evidence: what happened, where, and the proof. Never write 'always', 'never', or 'must'. A closed bead is history, not instructions for new work.

## Proof that claims and closes survive concurrency

The loop depends on two bd behaviors. When several actors claim one bead at once, exactly one wins. When several processes close different beads at once, every close lands.

[`scripts/check_bd_concurrency.py`](../scripts/check_bd_concurrency.py) races both on a throwaway store in a temp dir, 10 rounds each, and exits 1 on the first failure. It needs bd on PATH, so CI does not run it. Rerun it after a bd upgrade.

```sh
python3 scripts/check_bd_concurrency.py
```

Run the command from this skill's directory. Ten rounds take about 2.5 minutes.
