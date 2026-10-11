---
name: ticket-work
description: "Use for bead claims, run steps, review records, test records, and fix rounds. Route each ticket operation to its reference."
---

# Ticket work

Use this skill to record one assignment in the beads database.
The selected playbook chooses the steps and the gate order.

| Operation | Reference |
| --- | --- |
| Create or claim a run, record steps and phases, read or close a run | [Run records](references/run-records.md) |
| Execute `Review bead <gate> at <SHA> in <worktree>.` | [Review records](references/review-records.md) |
| Execute `Test bead <gate> at <SHA> in <worktree>.` | [Test records](references/test-records.md) |
| Execute `Fix bead <gate> at <SHA> in <worktree>.` | [Fix rounds](references/fix-rounds.md) |
| Pass text with quotes or several lines to a command | [Text files](references/text-files.md) |

Read the reference for the assigned operation. Keep its actor, scope, and evidence requirements.
