---
name: decisions
description: "Record and read what a project has settled: one append-only TSV row per decision, keyed by topic, read back with `decide now` and `decide log <topic>`. Use when the user says \"we decided\", \"record this decision\", or \"log that\", when she answers a design fork you asked about, and when you need to know what was decided about X, whether something has been settled already, or why the current approach is the current approach."
---

# Decisions

Record the row. Do not write the document. This skill exists so nobody
adds an ADR directory, a numbered rules file, or a decisions markdown
page to the project. Those go stale, and a stale decision is worse than
no decision, because a search returns it with the same confidence as a
true one.

Nothing here can go stale. The newest row for a topic is the decision in
force. There is no status field to disagree with reality, and no row is
ever edited. Superseding a decision means appending a newer row under
the same topic.

If a decision does not fit on one line, it is not crisp yet. Sharpen it,
then record it.

## Record a decision

Run the script from anywhere in the project:

```
skills/decisions/scripts/decide.py record <topic> <decision> <why> <evidence>
```

The five columns:

- **ts.** ISO8601 UTC, stamped by the script. Never passed in.
- **topic.** The stable key that groups one chain, slug-shaped:
  `save-format`, `auth-model`, `worktree-placement`. Reuse the exact
  topic when a later decision replaces an earlier one, or the chain
  breaks in two.
- **decision.** What was chosen, one line.
- **why.** The reason in plain words, one line. If the user chose it,
  her own sentence belongs here, not your paraphrase of it.
- **evidence.** A pointer, never prose: a commit SHA, a PR number,
  `file:line`, or a path.

Record when something is settled: a fork the user answered, a design
call made after weighing options, a constraint discovered the hard way,
an approach abandoned for a named reason. Skip the passing thought and
the step you are about to take anyway.

## Read what is settled

`decide.py now` prints the newest row for every topic, newest first. That
is the whole state of play, one topic per line. Read it before proposing
a design, and before asking the user something the project already
answered.

`decide.py log <topic>` prints every row for one topic, oldest first, so
you can walk the chain and see what changed and when. Read it when the
current decision surprises you, or when you are about to argue against
it.

## Where the file lives

The default is `.decisions.tsv` at the git root, or the working
directory outside a repo. Pass a path as the last argument to override
it. The script creates the file and its parent directory, writes the
header on first use, and adds the file to the repo's `.gitignore` once.

The log is a working artifact by default, like show-me-your-work's
trail. Commit it when the project wants its settled decisions to travel
with the code. Projects that keep agent scratch files in one place can
point the script at theirs, for example
`decide.py now .nikki-agents/decisions.tsv`.

Cells lose tabs and newlines so a row stays one line, and any cell
opening with `=`, `+`, `-`, or `@` gets a single quote in front of it,
so opening the file in a spreadsheet cannot run it as a formula.

## Not the same thing as show-me-your-work

Both are TSV logs. They answer different questions, and using the wrong
one loses the decision or floods the file.

- **`show-me-your-work`** is a trail of what happened during one run:
  every checkpoint, every pivot, in order. It is throwaway. When the run
  ends and the reviewer is satisfied, it can be discarded.
- **`decisions`** is what got settled. It is keyed by topic, it outlives
  the session, and it is what the next agent reads to avoid reopening a
  closed question. A decision is superseded, never deleted.

One run can produce twenty trail rows and no decisions, or one decision
after an hour of work. When a row in the run trail records a call the
next session must respect, record it here as well.

## Rules

- Append only. Never edit a past row, never delete one, never sort the
  file.
- One row is one decision. Two decisions are two rows.
- Reuse the topic when superseding. A new topic starts a new chain.
- No status, revised, or supersedes column. The order of the rows
  carries all three.
