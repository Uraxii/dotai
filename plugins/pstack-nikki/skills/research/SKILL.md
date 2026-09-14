---
name: research
description: >-
  Research at three levels of rigor, and the level gets named before any
  reading starts. Fires whenever a reply is about to cite a page from the web,
  which means storing the page and citing the stored copy instead of pasting a
  link. Fires when somebody wants one question looked up and answered from a
  few sources. Fires when material is being collected to feed analysis or a
  formal report, where the run hands over an audit trail a stranger can follow:
  one fact per row in your own words, the document behind each one, what each
  document is weak at, and a log of everything opened including the dead ends.
  Not for weighing options, scoring them, or committing to a course, and not
  for writing the report.
---

## Name the mode before you open anything

Three modes. Differ in how much collection discipline applies; handover follows
from that. Say which one before first search.

- **cite.** About to cite web page in a reply. Store page, cite stored copy.
  Minutes.
- **lookup.** One question, few sources, an answer. You answer it.
  references/lookup.md.
- **full.** Material that feeds analysis or formal report. Collection protocol
  below, plus handover contract.

Pick by where the output ends up. You know that before the first search. Full
whenever the run produces a file another person or a later run opens. Lookup
whenever the answer dies in this conversation once the asker has read it. One
page to put in front of somebody is cite.

Escalate when the answer starts wanting a judgment the sources do not settle.
Lookup that turns into weighing two accounts = full run not admitting it. cite
and lookup state the answer the sources support. They never score, rank,
weight, or state a likelihood; needing one is the escalation. Documents opened
before escalating still get source-record rows and consulted-log lines. Write
the collection plan after the fact, and say in the plan you wrote it that way.

Hand lookup and full to a subagent when the asking thread has other work and
the harness offers one. cite cheap enough inline. Delegated lookup returns the
answer plus the stored path of every document it cites.

## Meta-rule

Per-question operator instructions outrank every rule here. Instruction differs
from anything below -> instruction wins. In full mode, following the
instruction against a rule here is a deviation, and contract item 8 records it.
The three fields sit under the four checks. In cite and lookup, state an
override that drops the stored copy in the reply itself: no record exists to
carry it.

## cite mode

About to put a web page in front of somebody.

1. Open it and store it: the bytes, the retrieval path, the date, the licence
   terms.
2. Cite the stored copy. Title, originator, date, and where the copy sits. Bare
   link is not a citation: pages change, links rot, reader cannot check what you
   read. Where the copy sits has to be a path the reader can still open after
   this session ends. Scratch path that dies with the session does not qualify.
3. Take any quotation out of the stored copy, never out of memory and never out
   of a summary of it.

No handover file, no collection plan, no check record.

Licence forbids keeping the bytes -> cite by title and section, say the text is
not stored.

## Full mode

Full mode collects. Does not judge, does not draft. Nothing in this mode scores
an option, weights a criterion, states a likelihood, or commits to an answer.
Output is material somebody else reasons over. So fix the question first, plan
the collection against it.

### Words used in one sense only

- **Document.** Thing you opened and stored. Every table keys on it.
- **Originator.** Body or person that produced a document. A column, never a
  row.
- **Document id.** Short handle assigned when a document is first opened.
  Written same way in every table, so tables join.
- **Verbatim.** Text copied character for character out of a stored document.
  No other sense here.
- **Judgment.** One of the three note kinds. Nothing else here is called a
  judgment.
- **Originator reliability** and **document credibility.** The two rating axes,
  held apart.
- **Gap.** Hole in this run's evidence.

### The handover contract

Every full run hands over these eight, or names the ones that do not apply and
says why. A section quietly missing is what this contract exists to catch.

1. **The question.** The one question this collection answers, written before
   collecting, and the mode this run used. Where someone else set it, record
   their exact wording next to yours. GAO-12-208G, *Designing Evaluations*,
   chapter 2, is the standard being met: a researchable question is specific,
   measurable, and free of a presumed answer, and it is settled with whoever
   asked before the work runs.
2. **The collection plan.** What evidence would answer the question, and what
   evidence would break it. Written before the first document is opened. Not
   what the answer hinges on: that needs an answer, and there is not one yet.
3. **Fact notes.** One row per fact.
4. **Source records.** One row per document. Provenance is columns here, not a
   second table.
5. **Contrary material.** What contradicts other material you collected, or
   contradicts what the plan expected to find. Each row cites the consulted-log
   line it came from.
6. **Consulted log.** Every document opened, dead ends included, one line each
   on what it yielded or why it did not. The dead ends are the point: they are
   what stops the next run reopening what this one already ruled out.
   GAO-24-106786, *Government Auditing Standards*, chapter 8, sets the bar the
   log has to clear: the record has to let an experienced person who was not
   there work out what was done and what it produced.
7. **Gaps and the stop.** What was sought and refused, what could not be
   obtained, any claim you believe and cannot source, and which stopping
   condition ended the collection.
8. **Check record.** One row per check below, with its verdict. Never record a
   check you did not run: an unrun check is a verdict of not run. A check that
   stays failed carries a deviation block, and this item is where the block
   goes.

Hand it over as one Markdown file and name its path. Notes scattered through a
transcript are not an artifact.

### The three tables

**Fact notes.** Fact in your own words, document id, kind.

```
id    Fact                                  Doc    Kind        Why held
F1    Onboarding completion 14% in Q1       D3     fact
F2    Pricing drove the churn               D5     judgment
F3    Renewal terms hold through FY27       D2     assumption  D2 signed, no
                                                               notice clause
```

Mark every row fact, assumption, or judgment. Carry why an assumption is held.
Do not carry what follows if it is wrong: needs analysis nobody has done yet.

**Source records.** One row per document, eleven columns.

```
id | title | originator | date | locator | class
   | originator reliability | document credibility
   | derives from | licence | stored at
```

Title, originator, date, stable locator together = what lets someone else
render a citation and reopen the document. Filename alone is neither.

`class` = what kind of document it is, which decides what it will never tell
you. references/sources.md.

`derives from` names the document this one took its facts from, or `none`.

`licence` and `stored at` = the provenance: terms you may use the bytes under,
and where the bytes are.

**Consulted log.** One line per document opened.

```
D7  regulator's 2025 inspection report  the two findings on staffing
D8  agency press office, by phone       no answer in two attempts, dropped
D9  vendor status page                  current state only, no history, useless
```

### The eight steps

Steps 3 to 7 run once per candidate document and repeat. The stopping rule ends
the loop. references/stopping.md. Step 8 runs once.

1. **Fix the question.** Narrow an area to one question you can answer. Keep
   the question and its answer apart: you do not have the answer yet.
   references/collection.md.
2. **Plan the collection.** Name what would answer the question and what would
   break it. Then decide what to go after first. references/collection.md.
3. **Find candidates.** Record where each candidate came from as you find it,
   not afterwards. references/collection.md.
4. **Open it and decide whether it is usable.** Skim before you take notes.
   Assign the document id here. A document you reject still gets a
   consulted-log line. Cannot obtain it at all: references/refused.md.
5. **Rate it.** Originator reliability and document credibility, separately,
   plus what it derives from. references/sources.md and references/pitfalls.md.
6. **Take notes by transformation.** Understand the point, then write it in
   your own words. Copied wording drags originator's framing into an artifact
   meant to be free of it. Quote only where the exact wording is itself the
   fact, and mark the quotation as one. AFH 33-337, *The Tongue and Quill*,
   chapter 17, is the shape: facts, assumptions, and the standards in play get
   written down as separate labelled groups rather than blended into a
   narrative.
7. **Store it.** Keep the bytes, the retrieval path, the date, and the licence
   terms. Citation you cannot reopen is citation nobody can check. Take any
   verbatim quotation from the stored copy, never from a summary and never from
   memory.
8. **Check and hand over.** Run the four checks, record the verdicts as
   contract item 8, and fix a fail rather than noting it.

### The four checks

1. **The join.** Every document id in the fact notes appears in the source
   records and in the consulted log. Fails when the same document is called
   three names, and the consumer cannot tell which fact rests on what.
2. **The licence.** No note carries a source's wording as its own, and no bytes
   are stored for a document whose terms forbid it. Fails into a legal problem
   and into notes that smuggle the originator's framing.
3. **The stop.** Item 7 names the stopping condition that fired, plus every
   document sought and refused. An empty item 7 fails unless it states that
   nothing was refused and nothing was sought in vain. Fails when a collection
   that hit a wall arrives looking complete.
4. **The marks.** Every note carries a kind mark, and the mark matches what the
   note says. A causal claim marked `fact` is a judgment. Fails silently
   downstream, which is why it is a check and not a rule.

### A barred fix is a deviation

Step 8 says fix a fail rather than noting it. Two things bar the fix. Operator's
instruction overrides the check, under the Meta-rule. Or two rules here collide
and no wording satisfies both. Nothing else bars a fix, and a fail that is only
tedious to clear is still a fail.

Fix barred -> handover carries a deviation block, and contract item 8 is where
it sits. Each failed check carries its own block: two failed checks are two
blocks, never one covering both. Three fields, none optional:

- Which check, by its number in the four checks above. Where the instruction
  overrode something other than one of the four, a contract item or a rule
  from this file, name that instead. Those carry no number, and a deviation
  with nothing named in this field is an unrecorded fail.
- What authorises the deviation, quoted. The operator's instruction in the
  operator's own words, or both colliding rules with the side you took. A
  paraphrase authorises nothing.
- What the stranger reading the handover loses by it.

A deviation short a field is an unrecorded fail, which is what the check record
exists to stop. A document you were refused is not a deviation: that goes in
item 7 with the rest of the gaps.

### Do not

- Do not write a note you cannot trace to a stored document. An unsourced
  belief goes in item 7.
- Do not paste a source's wording into a note.
- Do not quote or store the bytes of a document whose licence forbids it. Cite
  it by title and section, and record the restriction in its row.
- Do not score, rank, weight, or choose between anything.
- Do not state a likelihood or a confidence level.
- Do not write the answer.
- Do not collect only what fits what you expected to find.
- Do not treat an originator's own account of itself as neutral.
- Do not count two documents that both copied a third as two.
- Do not drop a fact because it cannot be counted. Record it and say it resists
  measurement.
- Do not call one document by two names across two tables.

## Reference files

Load on demand. Each is this skill's own file.

- references/lookup.md. lookup mode end to end. Load when the mode is lookup.
- references/collection.md. Full mode steps 1 to 3, plus lookup mode's first
  step: fixing the question, planning what to go after and in what order,
  finding candidates.
- references/refused.md. What to do when a document is refused, walled, or does
  not exist. Load the moment a document cannot be obtained.
- references/sources.md. Full mode steps 4 and 5: classes of document and what
  each will not volunteer, rating originator reliability apart from document
  credibility, corroboration, circular reporting.
- references/stopping.md. When to stop collecting, and which stopping condition
  to name in item 7. Load when deciding whether to open another document.
- references/pitfalls.md. Failure modes full mode is built against, and the
  holes in this skill's own sourcing.
