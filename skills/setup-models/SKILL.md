---
name: setup-models
description: The user invokes this by name to change which model each delegated role runs on. Interviews them role by role, then rewrites the poteto-mode skill's model map so later spawns pin the new choices.
---

# Setup models

Edit rows in the `poteto-mode` skill's `models.md`: one row per label, an
ordered preference list of model names. A spawner walks the list and pins
the first name its harness accepts, so one row serves every harness at
once. Locate the file through the same skills install this skill was loaded
from; never hardcode an install layout or guess a home directory.

Model names this harness lets you pin on a spawned agent right now: `sonnet`,
`opus`, `haiku`, `fable`. Never write a name outside that set for this
harness, and never write one unconfirmed by the user. `fable`, `sol`, and
`luna` need explicit user permission stated in words this turn; silence is
not permission, leave that name out and say so.

1. **Load current state.** Read the `poteto-mode` skill's `models.md`; its
   rows are the current preference lists, one per label.

2. **Interview, per row.** Show the label and its current list. Confirm the
   first pinnable name that goes first for this harness, or ask the user
   which one does. No inline defaults, no assumed answer.

3. **Validate.** Reject any name outside the enumerated pinnable set.

4. **Write.** Overwrite only the confirmed rows, in the same
   `label: comma-separated list` format. Leave other harnesses' entries and
   every other line in the file untouched. Report the path written.
