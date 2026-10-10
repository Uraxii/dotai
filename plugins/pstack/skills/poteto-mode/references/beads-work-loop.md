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

Each shell call starts fresh. Set the actor variable on every call that runs a bd command.

```sh
export BEADS_ACTOR=<actor>
```

bd records claims and history under `BEADS_ACTOR`.

1. Claim the bead (`bd update <id> --claim`). If another actor holds it, the claim exits 1 and changes nothing. Stop and report the holder.
2. Read the scope (`bd show <id>`), including its NOTES section. A reopened bead holds the reason for the reopen there. If the comments end in a failed round, follow Fix a failed round.
3. A claim carries a lease that expires 5 minutes after the claim or the last heartbeat. During long work, send a heartbeat (`bd heartbeat <id>`) more often than that. A heartbeat writes no Dolt commit.
4. Write the commit message to the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) standard, and put the why in the commit body. Commit with this form:

   ```sh
   git commit -m "<type>(<scope>): <description>" -m "<why>" --trailer "Co-Authored-By: <attribution>"
   ```
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

## Gates after the writer

The coordinator runs two gates on each bead that changes code or tests, in this order. Each gate is a fresh agent that did not write the code. An Orchestrate unit uses the Verification section of `playbooks/orchestrate.md` instead.

1. **Reviewer.** Spawn `Review bead <id> at <SHA> in <worktree>.` as `reviewer-<id>`. The reviewer makes sure the code is solid. It edits no file.
2. **Tester.** After `verdict pass at <SHA>`, spawn `Test bead <id> at <SHA> in <worktree>.` as `tester-<id>`. The tester writes tests that stop the reviewed behavior from regressing. It changes only test files: tests, their fixtures, and test-only config. Production code and package scripts are not test files.

A bead that changes no code or tests, such as a docs-only or skill-prose bead, still gets the reviewer and skips the tester. A playbook can also spawn the reviewer on an `architect` sketch commit, before implementation starts. That review checks the design against the done-when, and it skips the tester.

The last failed round is the most recent `verdict fail at <SHA>` or `tests fail at <SHA>` comment. A tester failure counts as one must-fix item for each failing test.

When a gate fails, send the bead back to the writer. Append `<gate> fail at <SHA>, see comments` to the notes, reopen the bead if it is closed (per Reopen a closed bead), and spawn the writer with its same prompt. The writer follows Fix a failed round. Then the reviewer runs at the new head, and after its pass the tester runs again. On a sketch fail, the sketch's author revises the sketch and commits it, and the reviewer runs again at the new head. A gate fails at most 3 rounds on one bead. A sketch review and the code review after it count their fails apart, and the code review's rounds, including its last failed round, start after the sketch pass. After a third fail from the same gate, stop and report the open findings to the user.

The coordinator does not review the diff again. It checks these facts instead:

- The last result names the head SHA of the branch.
- When the tester committed, `git diff --stat <verdict SHA>..<head>` touches only test files.
- `git log <base>..<head>` and `git status --porcelain` agree with the bead. A close reason can name an older SHA when gate commits came after the close.
- Each item of the last failed round is marked `fixed` or `answered`.

Read the diff only when one of these checks fails, or when the bead has no verdict. In a Codex worktree, the diff read in the Base grants of `playbooks/delegate-to-codex.md` still applies.

## Fix a failed round

When the bead's comments end in a failed round, the writer does this before it commits or closes.

1. Fix each must-fix item, including each failing test. Do not weaken or delete a test the tester committed. If the test is wrong, say why in a comment and leave it for the reviewer.
2. Fix each should-fix-or-explain item, or answer it in a comment (`bd comment <id> --file <file>`) with a line `answered: <item>: <reason>`.

## Reviewer records the verdict

Set `BEADS_ACTOR` to the reviewer's actor name.

1. Read the done-when (`bd show <id>`) and the earlier rounds (`bd comments <id>`).
2. Review the combined diff of the bead's commits (`<base>..<SHA>`, the range the prompt or close reason names) against the scope and the done-when, with Claude Code's built-in code-review skill. The diff is an `architect` sketch or code. Judge it by the **principle-skeptical-review** principle skill, which holds the three tiers and the pass and fail rule. If there is a last failed round at `<old SHA>`, read `git diff <old SHA>..<SHA>` closely, because those commits are the fixes. Check that no test the tester committed was weakened or deleted without a reason you accept.
3. Write the verdict to a file. The first line is `verdict pass at <SHA>` or `verdict fail at <SHA>`. Then list the findings under the three tiers. Mark each item from the last failed round `fixed`, `answered: <reason>`, or `still open`. Add the file as a comment (`bd comment <id> --file <file>`). The SHA ties the verdict to the commit that was reviewed.

## Tester records the result

Set `BEADS_ACTOR` to the tester's actor name.

1. Read the done-when (`bd show <id>`), the last verdict, and your own last result if there is one (`bd comments <id>`). Check that each earlier failure now passes. If the reviewer accepted that one of your tests is wrong, fix that test.
2. Start from the writer's tests and add what they miss. Write tests that fail if the reviewed behavior regresses. Cover the done-when, the edge cases, and the failure paths, per the **principle-test-behavior-not-implementation** principle skill. Change only test files. If a test needs a production change, do not make it. Report it as a failure, and the bead goes back to the developer.
3. Run the new tests and the project's full suite. A test named in the bead's `baseline failures` comment does not fail the gate, unless the done-when says it must pass. Name it in the result. Commit the tests with the commit form in Worker claims, commits, and closes.
4. Write the result to a file. The first line is `tests pass at <SHA>` or `tests fail at <SHA>`, where `<SHA>` is the new head. Then give the count passed out of the count run, each failure with steps to reproduce it, and the coverage gaps. A pass does not prove the code is correct, so name what the tests do not cover. Add the file as a comment (`bd comment <id> --file <file>`).

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
