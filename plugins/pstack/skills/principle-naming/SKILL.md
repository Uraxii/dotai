---
name: principle-naming
description: "Use when naming or renaming anything another reader will meet later: a file, a directory, a report or document, a scratch artifact, a variable, function, type, constant, branch, or commit subject. Fires before writing any new file, whenever a name is about to carry a generic stem, a number, a date, a version word, an acronym, or a codename, and when reviewing names in a diff. Exists to stop one failure: names that only decode for someone who was in the session."
---

## Every name

- Say what the thing IS and its effect. Not mechanism, metaphor, timing.
- No structure filler as identity: manager, controller, handler, helper, util, service, wrapper, data, info, object, item.
- No scheduling word as identity: deferred, pending, delayed, async, lazy.
- One word per concept, one concept per word. Two different things named `report` in one tree -> one is wrong.
- Descriptiveness scale with reach. Three-line loop counter may be `i`. Filename, directory, export, committed document: full words.

## Filesystem names

- Subject plus kind, two elements minimum. `naming-research-findings.md`, not `findings.md`.
- Series artifact (session log, decision record, dated report): ISO prefix `YYYY-MM-DD-`, so lexical sort equal chronological sort.
- Version numbers yes (`-v001`). Version words no (`final`, `latest`, `new`, `FINAL_FINAL`).
- Numbers zero-padded to three digits, never the only thing telling two files apart. `output2.md` rejected.
- One canonical file, not near-duplicate dumps told apart by suffix.

