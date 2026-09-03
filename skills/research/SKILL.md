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

Three modes. They differ in how much of the collection discipline applies, and
what gets handed over follows from that. Say which one you are in before the
first search.

- **cite.** You are about to cite a web page in a reply. Store the page, cite
  the stored copy. Minutes.
- **lookup.** One question, a few sources, an answer. You answer it yourself.
- **full.** Material that will feed analysis or a formal report. The collection
  protocol below, with the handover contract.

Pick by where the output ends up, which you know before the first search. The
run is full whenever it produces a file another person or a later run opens.
The run is lookup whenever the answer dies in this conversation once whoever
asked has read it. One page you want to put in front of somebody is cite.

Escalate when the answer starts wanting a judgment call the sources do not
settle. A lookup that turns into weighing two accounts against each other is a
full run that has not admitted it yet. Escalating early costs a restatement of
the question. Escalating late costs the run.

Documents you opened before escalating still get source-record rows and
consulted-log lines. Write the collection plan after the fact and say in the
plan that you wrote it that way.

cite and lookup state the answer the sources support. They still do not score,
rank, weight, or state a likelihood. The moment the answer needs one of those,
escalate.

Hand lookup and full to a subagent when the thread that asked has other work
to get on with and the harness offers one. cite is cheap enough to do inline.
A delegated lookup returns the answer and the stored path of every document it
cites.

## Meta-rule

Per-question instructions from the operator outrank every rule here. Where the
operator's instruction differs from anything below, the instruction wins. In
full mode, following the instruction against a rule here is a deviation, and
contract item 8 records it. The three fields sit under the four checks. In cite
and lookup, state an override that drops the stored copy in the reply itself,
because no record exists to carry it.

## cite mode

You are about to put a web page in front of somebody.

1. Open it and store it: the bytes, the retrieval path, the date, and the
   licence terms.
2. Cite the stored copy. Title, originator, date, and where the copy sits. A
   bare link is not a citation. Pages change, links rot, and the reader cannot
   check what you actually read. Where the copy sits has to be a path the
   reader can still open after this session ends. A scratch path that dies
   with the session does not qualify.
3. Take any quotation out of the stored copy, never out of memory and never
   out of a summary of it.

No handover file, no collection plan, no check record.

Where the licence forbids keeping the bytes, cite by title and section and say
the text is not stored.

## lookup mode

One question, a handful of documents, an answer that goes back to whoever
asked.

1. Write the question in one sentence. If you cannot, you have an area rather
   than a question, and the "Fix the question" section of
   references/collection.md fixes that. The rest of that file is full mode's.
2. Read a few documents, preferring the body that created or holds the data
   over anyone reporting on it. Store each one the way cite mode stores one.
   Where two documents look independent, check that they do not both trace
   back to one origin before you treat them as corroborating.
3. Answer directly. Every claim cites the stored document it rests on.
4. Note the dead ends in a sentence: what you opened that gave you nothing, so
   the next run does not walk the same path.

The output is the answer. No handover contract, no check record, no collection
plan, no tables. Mark a claim you are inferring rather than reading, so the
reader can tell the two apart.

Where the documents disagree, or where the answer needs somebody to weigh
them, that is full mode. Say so and switch.

## Full mode

Full mode collects. It does not judge and it does not draft. Nothing in this
mode scores an option, weights a criterion, states a likelihood, or commits to
an answer. The output is material somebody else reasons over.

The split is not an invention. JP 2-0, *Joint Intelligence*, chapter I, runs
planning and direction, collection, processing and exploitation, analysis and
production, and dissemination as separate steps of one process. Full mode is
the first three. Everything after the material is in hand belongs to whoever
takes it.

Collecting is not the same as collecting blind. Heuer, *Psychology of
Intelligence Analysis*, Part II chapter 5, attacks the model where an analyst
gathers fragments and waits for a picture to assemble itself, and prefers the
diagnostic shape: observe, form candidate explanations, then collect narrowly
to tell them apart. So fix the question first and plan collection against it.
The line you do not cross is committing to the answer.

### Words used in one sense only

- **Document.** The thing you opened and stored. Every table keys on it.
- **Originator.** The body or person that produced a document. A column, never
  a row.
- **Document id.** A short handle assigned when a document is first opened.
  Written the same way in every table so the tables join.
- **Verbatim.** Text copied character for character out of a stored document.
  The word carries no other sense here.
- **Judgment.** One of the three note kinds. Nothing else in this skill is
  called a judgment.
- **Originator reliability** and **document credibility.** The two rating
  axes, held apart.
- **Gap.** A hole in this run's evidence.

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

Needed every full run, so they are here rather than behind a read.

**Fact notes.** The fact in your own words, the document id, and the kind.

```
id    Fact                                  Doc    Kind        Why held
F1    Onboarding completion 14% in Q1       D3     fact
F2    Pricing drove the churn               D5     judgment
F3    Renewal terms hold through FY27       D2     assumption  D2 signed, no
                                                               notice clause
```

Mark every row fact, assumption, or judgment. ICD 203, *Analytic Standards*,
section D, requires information, assumptions, and judgments be distinguishable
on sight, and requires an assumption carry why it is held. A judgment written
in the grammatical form of a fact is the most expensive error in the handover,
because nothing downstream can detect it.

Carry why an assumption is held. Do not carry what follows if it is wrong:
that needs analysis nobody has done yet.

**Source records.** One row per document, eleven columns.

```
id | title | originator | date | locator | class
   | originator reliability | document credibility
   | derives from | licence | stored at
```

Title, originator, date, and a stable locator together are what lets someone
else render a citation and reopen the document. A filename alone is neither.

`class` is what kind of document it is, which is what decides what it will
never tell you. references/sources.md.

`derives from` names the document this one took its facts from, or `none`.
Without it, two documents that both copied a third arrive looking like two
independent confirmations.

`licence` and `stored at` are the provenance: under what terms you may use the
bytes, and where they are.

**Consulted log.** One line per document opened.

```
D7  regulator's 2025 inspection report  the two findings on staffing
D8  agency press office, by phone       no answer in two attempts, dropped
D9  vendor status page                  current state only, no history, useless
```

Write the useless ones down. A dead end recorded once is a dead end nobody
walks twice.

### The eight steps

Steps 3 to 7 run once per candidate document and repeat. The stopping rule
ends the loop. Step 8 runs once.

1. **Fix the question.** Narrow an area to one question you can answer. Keep
   the question and its answer apart: the question is what you were asked, the
   answer is what the collection turns out to support, and you do not have it
   yet. Where somebody else set the question, record their wording and settle
   it with them before working. references/collection.md.
2. **Plan the collection.** Name what would answer the question and what would
   break it. Then decide what to go after first. references/collection.md.
3. **Find candidates.** Record where each candidate came from as you find it,
   not afterwards. references/collection.md.
4. **Open it and decide whether it is usable.** Skim before you take notes.
   Assign the document id here. A document you reject still gets a
   consulted-log line.
5. **Rate it.** Originator reliability and document credibility, separately,
   plus what it derives from. references/sources.md and references/pitfalls.md.
6. **Take notes by transformation.** Understand the point, then write it in
   your own words. Copying the wording carries the originator's framing
   forward into an artifact meant to be free of it. Quote only where the exact
   wording is itself the fact, and mark the quotation as one. AFH 33-337, *The
   Tongue and Quill*, chapter 17, is the shape being followed: facts,
   assumptions, and the standards in play get written down as separate labelled
   groups rather than blended into a narrative.
7. **Store it.** Keep the bytes, the retrieval path, the date, and the licence
   terms. A citation you cannot reopen is a citation nobody can check. Take any
   verbatim quotation from the stored copy, never from a summary of it and
   never from memory.
8. **Check and hand over.** Run the four checks, record the verdicts as
   contract item 8, and fix a fail rather than noting it.

### When to stop

Heuer, *Psychology of Intelligence Analysis*, Part II chapter 5, section "When
Does New Information Affect Our Judgment?", ranks four kinds of additional
material. Two still change the answer:

- Material that changes the value you would put on a variable already known to
  matter.
- Material that changes which variables matter, or how they connect.

Two do not, and they are the bulk of what arrives: more detail on variables
already in play, and further variables that turn out not to move anything.

So stop when the next document would only add detail to what you already hold.
Keep going while it could still revise a key value or the shape of the
problem. Then say in contract item 7 which of those two conditions fired.

The finding the chapter is built on is why this matters: past the minimum
needed for an informed judgment, more material generally stops raising accuracy
and keeps raising confidence. A thick collection feels like a good one.

### The four checks

Four, because the other contract items are readable straight off the artifact
and a check that re-asks the contract cannot fail. These four test what no
single section shows.

Two questions sit behind them, and GAO-24-106786, *Government Auditing
Standards*, chapter 8, is where they come from. Is the evidence sufficient,
meaning is there enough of it for the weight put on it. Is it appropriate,
meaning is it relevant, valid, and reliable for the point it is being used to
make. Quantity never makes up for the wrong kind.

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

Step 8 says fix a fail rather than noting it. Two things bar the fix. The
operator's instruction overrides the check, under the Meta-rule. Or two rules
here collide and no wording satisfies both at once. Nothing else bars a fix,
and a fail that is only tedious to clear is still a fail.

Where the fix is barred, the handover carries a deviation block, and contract
item 8 is where it sits. Each failed check carries a block of its own: two
failed checks are two blocks, never one covering both. Three fields, none
optional:

- Which check, by its number in the four checks above. Where the instruction
  overrode something other than one of the four, a contract item or a rule
  from this file, name that instead. Those carry no number, and a deviation
  with nothing named in this field is an unrecorded fail.
- What authorises the deviation, quoted. The operator's instruction in the
  operator's own words, or both colliding rules with the side you took. A
  paraphrase authorises nothing.
- What the stranger reading the handover loses by it.

A deviation short a field is an unrecorded fail, which is what the check
record exists to stop. A document you were refused is not a deviation: that
goes in item 7 with the rest of the gaps.

### Do not

- Do not write a note you cannot trace to a stored document. A claim you
  believe and cannot source goes in item 7, not in the notes.
- Do not paste a source's wording into a note.
- Do not quote or store the bytes of a document whose licence forbids it. Cite
  it by title and section, and record the restriction in its row.
- Do not score, rank, weight, or choose between anything.
- Do not state a likelihood or a confidence level.
- Do not write the answer.
- Do not collect only what fits what you expected to find.
- Do not treat an originator's own account of itself as neutral.
- Do not count two documents that both copied a third as two.
- Do not drop a fact because it cannot be counted. Record it and say it
  resists measurement.
- Do not call one document by two names across two tables.

## Reference files

Load on demand. Each is this skill's own file.

- references/collection.md. Full mode steps 1 to 3, and lookup mode's first
  step: fixing the question, planning what to go after and in what order,
  finding candidates, and what to do when a document is refused.
- references/sources.md. Full mode steps 4 and 5: the classes of document and
  what each one will not volunteer, rating originator reliability apart from
  document credibility, corroboration, and circular reporting.
- references/pitfalls.md. The failure modes full mode is built against, and
  the holes in this skill's own sourcing.
