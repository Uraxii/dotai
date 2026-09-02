---
name: research
description: >-
  Gather the material a question gets answered from, and hand it over as an
  audit trail a stranger can follow: one fact per row in your own words, the
  document behind each one, what each document is weak at, and a log of
  everything opened including the dead ends. Fires when a question needs
  evidence before anyone can answer it, when a claim is about to rest on
  something nobody stored, and whenever a reply is about to cite a page from
  the web. Not for judging what the material means, and not for writing it up.
---

## Meta-rule

Per-question instructions from the operator outrank every rule here. Where the
operator's instruction differs from anything below, the instruction wins.
Following the instruction against a rule here is a deviation, and contract
item 8 records it. The three fields sit under the four checks.

## Scope: this skill collects

It does not judge and it does not draft. Nothing here scores an option, weights
a criterion, states a likelihood, or commits to an answer. The output is
material somebody else reasons over.

The split is not an invention. JP 2-0, *Joint Intelligence*, chapter I, runs
planning and direction, collection, processing and exploitation, analysis and
production, and dissemination as separate steps of one process. This skill is
the first three. Everything after the material is in hand belongs to whoever
takes it.

Collecting is not the same as collecting blind. Heuer, *Psychology of
Intelligence Analysis*, Part II chapter 5, attacks the model where an analyst
gathers fragments and waits for a picture to assemble itself, and prefers the
diagnostic shape: observe, form candidate explanations, then collect narrowly
to tell them apart. So fix the question first and plan collection against it.
The line you do not cross is committing to the answer.

## Words used in one sense only

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

## The handover contract

Every run hands over these eight, or names the ones that do not apply and says
why. A section quietly missing is what this contract exists to catch.

1. **The question.** The one question this collection answers, written before
   collecting. Where someone else set it, record their exact wording next to
   yours. GAO-12-208G, *Designing Evaluations*, chapter 2, is the standard
   being met: a researchable question is specific, measurable, and free of a
   presumed answer, and it is settled with whoever asked before the work runs.
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

## The three tables

Needed every run, so they are here rather than behind a read.

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

## The eight steps

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
   plus what it derives from. references/sources.md.
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

## When to stop

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

## The four checks

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

## A barred fix is a deviation

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

## Do not

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

## Failure modes

- **Stacked evidence.** Only the material supporting the emerging picture gets
  collected, and the collection looks thorough. Named, with primacy of print
  and false authority, in AFH 33-337, *The Tongue and Quill*, chapter 5.
- **Memory laundering.** A note with no document behind it, sourced to general
  knowledge. Every figure looks sourced.
- **Circular reporting read as corroboration.** Heuer chapter 10: consistent
  material misleads when it is correlated or redundant, because agreement
  between two copies of one source is not agreement.
- **The self-portrait taken as fact.** An originator's own account of itself
  entered without the discount it needs.
- **Confidence growing with volume.** Covered above under when to stop.
- **The vivid case beating the aggregate.** Heuer chapter 10: one memorable
  example outweighs the numbers unless you make it not.

## Stated limits

Holes, named so nothing is quietly asserted.

- **The stopping trigger.** A design decision. The chapter cited above
  justifies having a stopping rule and ranks what is still worth collecting,
  then qualifies its own finding, allows that more material sometimes does
  improve accuracy, and never says how to recognize the minimum for an
  informed judgment. It is a warning about diminishing returns, not a
  procedure.
- **Own words.** No check can catch a paraphrase that is really a copy without
  the source open beside it. It is a rule, not a check.
- **When a copy stands in for an original.** A mirror, a re-host, or a scan may
  be all you can reach. No standard here settles when that is acceptable.
  Record which host served it and what failed at the original, and let the
  reader judge.
- **Quoting only from the stored copy.** A convention, not a sourced rule.
  Nothing in the documents behind this skill says a quotation has to come from
  stored bytes rather than from a summary. It is here because a quotation taken
  from a summary is a quotation of the summarizer, and nobody downstream can
  tell.
- **One fact per row.** A format decision. The rule to transform rather than
  copy, and the three kind marks, are sourced. The row schema is not.
- **Whether an originator is reliable in general.** No adjudicator. Name the
  absence, write down the standard you used, and mark it as your own.

## Reference files

Load on demand. Each is this skill's own file.

- references/collection.md. Steps 1 to 3: fixing the question, planning what
  to go after and in what order, finding candidates, and what to do when a
  document is refused.
- references/sources.md. Steps 4 and 5: the classes of document and what each
  one will not volunteer, rating originator reliability apart from document
  credibility, corroboration, and circular reporting.
