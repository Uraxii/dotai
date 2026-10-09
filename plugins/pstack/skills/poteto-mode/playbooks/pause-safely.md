### Pause safely

**You own a clean stop. Leave a checkpoint a cold-start agent can resume from.** This is explicit only. On "keep going", "going to bed, keep going", or "don't stop", do not pause.

1. Stop at a safe boundary. Finish the current atomic step or back out of it. Never stop mid-edit in a known-broken state. Start nothing new, and cancel any nested subagents.
2. Take no irreversible action to pause. No PR and no push unless you already had one out.
3. Make the work durable. Commit uncommitted edits as one clear `wip:` commit on the current branch so nothing is lost. If the tree is broken, say so in the commit body in one line.
4. Write one current-state note on each in-progress bead you hold and on each one held by a subagent you cancelled in step 1. A subagent runs under its own actor (`<role>-<id>`), so filtering by your actor misses its beads. List every in-progress bead with its assignee, keep the beads assigned to you or to a cancelled subagent, and leave the beads other actors hold alone.

   ```sh
   bd list --status in_progress --json | jq -r '.[] | "\(.id)\t\(.assignee)"'
   ```

   For each kept bead, set its notes (`bd update <id> --notes "<branch>, wip <SHA>, verified: <what passed>, next: <first step on resume>"`). `--notes` replaces the bead's notes, so the note holds the current state only.
5. Put the artifacts the user asked to keep for after resume into beads. Keep the user's wording, every item, and the order.
   - A checklist becomes the bead's done-when. Set the bead's acceptance (`bd update <id> --acceptance "<checklist>"`).
   - An open question becomes a bead that blocks the work. Create a bead that blocks it (`bd create "<question>" --labels question --deps blocks:<id>`), or a human gate (`bd gate create --type human --blocks <id> --title "<question>"`). Ten questions means ten blockers.
6. Release the merge slot only if you hold it. `bd merge-slot release` exits 1 when the slot is free or missing, so check the holder first. A free or missing slot has no holder, and the block below then does nothing and exits 0.

   ```sh
   if [ "$(bd merge-slot check --json | jq -r '.holder // empty')" = "<actor>" ]; then
     bd merge-slot release --holder <actor>
   fi
   ```
7. Read each bead back (`bd show <id>`). Check that the note, the acceptance, and every blocker are there before you declare the pause ready.

**Reply:** where you are in the loop, the beads you noted, what is still only in your head, the commits you made and whether the tree is clean, and the first action on resume. This is a pause, not a final report.
