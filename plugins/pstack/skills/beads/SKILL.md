---
name: beads
description: Track, create, claim, and close issues in a repo with bd (beads). Use for "what can I pick up", dependency links between issues, or any bd command.
---

# Beads

Run `bd` directly in the project's working directory. It is a local binary
with its own `.beads/` database per project; nothing else to configure.

## Rules

- `bd ready` lists claimable work: open issues with no active blocker.
  `bd list --status open` is a different query; it still includes blocked
  issues.
- `bd update -d "..."` replaces the whole description. To add context
  without losing history, use `bd note <id> "text"`, which appends.
- Deletion is a human, out-of-band decision. Never run `bd delete`.
- The user never reads the tracker, so a bare ID names nothing to them. In
  anything the user reads, including replies, summaries, commit messages, PR
  titles and bodies, and handoffs, say what the work is and put the ID in
  parentheses: `closed the retry-loop fix (abc.12)`, not `closed abc.12`.
  IDs stay bare in `bd` commands, notes, links, and messages between agents.
- Link types: `blocks`, `tracks`, `related`, `parent-child`,
  `discovered-from`.
- Status values: `open`, `in_progress`, `blocked`, `deferred`, `closed`,
  `pinned`, `hooked`.
- Priority (`-p`): `0` (critical) to `4` (backlog). Default `2`.

## Scope

Beads is the local issue tracker, nothing more.

Use it for:

- Tickets: `create`, `update --claim`, `close`, `note`, `search`, `show`,
  `children`.
- Dependency edges and the frontier: `link`, `dep`, `ready`.
- The wayfinder map: a parent issue with child tickets.

Not for: memory, session recovery, rules injection, workflow templates, or
git.

## Invocation

Run `bd` from the project root. Add `--json` only when a script parses
the output.

```bash
bd <verb> ...
```

If `.beads/` is missing, initialize once:

```bash
bd init --non-interactive --skip-agents
```

## Verbs

| Verb | Use |
|---|---|
| `create TITLE` | New issue. `-p N` priority, `-d TEXT` description, `-l LABEL` |
| `list` | List issues. `--status S` filters |
| `ready` | Claimable work: open, no active blocker |
| `show ID` | Issue detail |
| `update ID` | Change fields. `--claim` claims it, `-s STATUS` sets status |
| `close ID` | Close an issue. `-r REASON` |
| `note ID TEXT` | Append to notes; does not replace the description |
| `link ID1 ID2` | Add a dependency. `-t TYPE`, default `blocks` |
| `dep ID` | Inspect dependency edges: `dep list`, `dep tree` |
| `search QUERY` | Search titles and IDs; excludes closed by default |
| `children ID` | List children of a parent issue |

## Install

If a `bd` call fails with `command not found`, follow `references/SETUP.md`,
then rerun `bd version` before retrying the call.
