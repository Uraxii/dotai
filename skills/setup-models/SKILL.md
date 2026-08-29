---
name: setup-models
description: The user invokes this by name to change which models delegated work runs on. Interviews them per label in the poteto-mode skill's models.md, validates each name against what the current harness can pin, and rewrites the confirmed rows so later spawns pick the new preferences.
---

# Setup models

You edit the `poteto-mode` skill's `models.md` on the user's request. One
row per label, an ordered preference list of model names; a spawner walks
the list and pins the first name its harness accepts, so one row serves
every harness. Locate the file through the skills install this skill was
loaded from; never hardcode an install layout or guess a home directory.

1. **Discover the pinnable set.** Enumerate the model names the current
   harness accepts on a spawned agent this session (its spawn tool's model
   parameter, or its documented model list). That set, plus the harness
   aliases `models.md` maps to full names, is the only set you may write.
   Never write a name outside it, and never write one unconfirmed by the
   user. `fable`, `sol`, and `luna` need explicit permission stated in words
   this turn; silence is not permission, leave the name out and say so.

2. **Load current state.** Read `models.md`; its rows are the current
   preference lists, one per label.

3. **Interview, per row.** Show the label and its current list. Ask which
   name goes first for this harness and whether any entry should move or go.
   No inline defaults, no assumed answer.

4. **Validate.** Reject any name outside the discovered set.

5. **Write.** Overwrite only the confirmed rows, in the same
   `label: comma-separated list` format. Leave every other line untouched.
   Report the path written and the rows changed.
