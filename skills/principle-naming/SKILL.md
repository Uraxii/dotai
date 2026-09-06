---
name: principle-naming
description: Use when naming or renaming anything another reader will meet later: a file, a directory, a report or document, a scratch artifact, a variable, function, type, constant, branch, or commit subject. Fires before writing any new file, whenever a name is about to carry a generic stem, a number, a date, a version word, an acronym, or a codename, and when reviewing names in a diff. Exists to stop one failure: names that only decode for someone who was in the session.
---

# Naming

## Cold-reader test

Reader was not in this session, has not opened the thing. Can they say what
it holds from the name alone? No -> rename. Unsure -> fill in:

    A reader who has not opened <name> can tell it holds: <one sentence>.

Sentence need a word the name lack -> put the word in.

Why a test: 334 developers naming one concept picked the same name 6.9% of
the time, so "pick a meaningful name" is uncheckable. "Can a cold reader
decode THIS name" is checkable. Rules below are that check made mechanical.

## Every name

- Say what the thing IS and its effect. Not mechanism, metaphor, timing.
- No structure filler as identity: manager, controller, handler, helper,
  util, service, wrapper, data, info, object, item.
- No scheduling word as identity: deferred, pending, delayed, async, lazy.
- One word per concept, one concept per word. Two different things named
  `report` in one tree -> one is wrong.
- No joke, pun, codename, session in-joke. Read fine only to who was there.
- Acronym only with its own Wikipedia article or a project glossary entry.
  Else spell out. Never drop internal letters (`bkgd`, `evntHndlr`).
- Descriptiveness scale with reach. Three-line loop counter may be `i`.
  Filename, directory, export, committed document: full words.

## Filesystem names

- Subject plus kind, two elements minimum. `naming-research-findings.md`,
  not `findings.md`. Check: strip extension, count elements.
- Kebab-case, lowercase ASCII, no spaces. Letters, digits, hyphens, one
  dot before the extension.
- Series artifact (session log, decision record, dated report): ISO prefix
  `YYYY-MM-DD-`, so lexical sort equal chronological sort.
- Version numbers yes (`-v001`). Version words no (`final`, `latest`,
  `new`, `FINAL_FINAL`).
- Numbers zero-padded to three digits, never the only thing telling two
  files apart. `output2.md` rejected.
- One canonical file, not near-duplicate dumps told apart by suffix.
- Roughly 25 to 35 characters. Full path under 255.

Banned as whole name or leading element:

    notes output result results report summary analysis findings data
    info doc document file temp tmp misc stuff new old test draft
    untitled final

Generated infrastructure paths (task ids, worktree hashes, harness plan
slugs) not yours to name. Rules bind names YOU choose.

## Identifiers

- Constants and fields carry domain plus units. `REVIVE_TIME_SEC`, not
  `TIME_EPSILON`. `cooldown_remaining`, not `timer`.
- Parameter names outrank local names. Spend care there first.
- No type-encoded prefix. Compiler and editor track type.
- Never `l`, `O`, `I` alone. Some fonts render them `1` and `0`.
- Initialism one case throughout, `URL` not `Url`. Style guide pick which.
- Rename everywhere in one change: code, tests, diagrams, spec text,
  commit messages, tickets.

Full code-naming treatment sit in `principle-code-quality`.

## Not rules, despite popular belief

State when someone assert them as rules.

- camelCase over snake_case. Measured no better. Eye-tracking replication
  found camelCase 20% slower to read (p=0.035).
- Always spell out in full. Well-formed abbreviations measured no worse
  than full words. Single letters ARE worse.
- Longer is safer. Clarity often come from brevity (Kernighan and Pike).
  Length serve reach, not virtue.

## Sources

Claims table (evidence strength, source weaknesses) plus 84 stored sources:
`.nikki-agents/research/naming-conventions/naming-research-findings.md`
in the dotai repo. Kb pages `naming-artifacts-for-a-reader-with-no-context`
and `identifier-naming-what-the-evidence-supports`.
