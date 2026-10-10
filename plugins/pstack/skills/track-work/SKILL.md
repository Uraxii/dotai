---
name: track-work
description: "Track and coordinate local work with the beads plugin: one issue per delegated unit, claimed by its owner, with findings and verdicts as comments and the result as the close reason. Use when you delegate a unit, pick up or pause work, record a follow-up, or need to know what is ready."
---

# Track work

pstack tracks local work in [beads](https://github.com/gastownhall/beads) through the beads plugin. Use the plugin's skills. Do not write a tracking file or a custom protocol.

| Job | beads-plugin skill |
|---|---|
| Record a unit of work, a follow-up, or a defect found mid-task. Put the scope in the description and the done-when in the acceptance criteria. | `beads:create` |
| Claim a unit before you work on it. Change its status or fields. | `beads:update` |
| Read a unit's scope and history before you start, review, or pick it up. | `beads:show` |
| Record a finding, a gate verdict, or a pause point on a unit. | `beads:comments` |
| Make one unit wait for another. | `beads:dep` |
| Find the units that are ready to start, or see which are blocked. | `beads:ready`, `beads:blocked` |
| Find units by text or by filter. | `beads:search`, `beads:list` |
| Close a finished unit. Put the result, the check result, and the head SHA in the reason. | `beads:close` |

The beads plugin owns how each operation works. Read its skill when you need the details. When the plugin is not installed for your harness, run the `bd` subcommand of the same name. When beads is not available at all, track the work in the session's task list.
