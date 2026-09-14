# checklist.md: the step 8 check layer

Run at step 8, before you send, against the finished draft and the artifacts
the steps produced. Process, not precept. Work it top to bottom.

Every check traces to a ruling; the bracket tag names it. A check enforcing
material another file owns points to that file. Do not re-derive the rule
here; open the file the tag or the "see" clause names.

Order of the step:

1. Run the key assumptions check, second run (below). Record its output.
2. Run the sensitivity test (below). Record its output.
3. Run the checks (below) against the draft and the artifacts. Score every
   one of them on the scoreboard (below) as you go, before you write the
   deviations block.
4. Run `bash <this-skill-directory>/scripts/check-report.sh <report>
   <materials-dir>`, where the materials directory is the folder the
   operator named. Fix what it names, then run it again. A report you send
   while it still fails is unfinished.
5. Run the three-pass edit, in order.

## The checks

Each is a pass/fail item. A fail is a fix. Two things are not that.

An input the analysis never produced is a gap this skill cannot close. Say so
and send it back; that is step 5, not a deviation.

A fix that is barred is a recorded deviation. Barred means an operator
instruction overrides the check, or two rules in this skill collide with no
way to satisfy both by any rewriting. Nothing else is barred.

Record deviations in the deviations block, `## Deviations`. Every check that
stays failed gets its own entry in that block, so two failed checks are two
entries, never one merged entry covering both. However many entries it holds,
the deviations block stays one end-matter item of an admissible type
(check 2). One line per entry, opening `- Check N.`, or `- Rule <name>.` for
a rule outside the numbered list. Three fields per entry, all required:

- The check not met, by its number on this list. A rule outside the numbered
  checklist is cited by name instead. Never a file:line in the report; the
  number or the name is the citation.
- The rule that authorises it, quoted: the operator's instruction in the
  operator's own words, or both colliding rules and the side you took. A rule
  named but not quoted is not an authoriser.
- What the reader loses by it.

An entry missing a field is an unrecorded fail.

## The scoreboard

A sibling file, `<report-name>.checks.md`, beside the report. Score every
check here first; the deviations block is a transcription of this file's
`not-met` rows, never a fresh judgment made at write time.

One line, `Format: <the paper format chosen>`, then a markdown table, one row
per numbered check: header row, separator row, one row per check, every row
opening and closing with `|`. This is the shape the checker parses. Copy it,
do not paraphrase it:

| check | verdict | authoriser | quoted rule | reader loses |
|---|---|---|---|---|
| 1 | met |  |  |  |

Verdict is one of `met`, `not-met`, `n-a`. A `met` or `n-a` row leaves
`authoriser`, `quoted rule`, and `reader loses` blank. A `not-met` row fills
all three — this check's deviation fields, scored once here and transcribed
once into the deviations block.

Your working directory is the report's, not this skill's, so run the checker
by this skill's own path:

`bash <this-skill-directory>/scripts/check-report.sh <report> <materials-dir>`

The materials directory is the folder the operator named. It has to hold
the report's own directory, so a report written into an `out/` subfolder
still gets compared against everything above it. The checker refuses to run
without it rather than fall back to the directory you chose yourself.

It diffs the deviations block against the `not-met` rows, checks every
end-matter item against the five admissible types (check 2), checks the
format-elements note against what the format claims (check 5), and scans
the materials directory for a 40-plus-word span pasted verbatim into the
report or into its notes file (check 22). The scan is the one test here
that reads the report itself rather than the scoreboard the writer filled
in; a matching span is not itself a fail, but check 22 must then be scored
`not-met` with the deviation recorded, an `## Attachment:` section
included. Fix what it names.

The numbered checks:

1. The first paragraph answers the written-out question, with the reasons
   grouped into categories, not a flat list. [contract]
2. The first paragraph announces the order; the body follows it exactly, with
   nothing beyond what the paragraph promised. A section bolted on the end
   fails this. Whatever sits outside the announced body is end matter, and
   every end-matter item is one of these five types. The list is closed; the
   count is not. Zero, one, or several items of a type all pass. Each item
   carries the heading named here; that is how scripts/check-report.sh reads
   the type.
   - The source list. `## Sources`.
   - The deviations block. `## Deviations`.
   - The format-elements note check 5 requires when a named format claims an
     excluded element. `## Format elements`.
   - The cover letter an external report carries, check 11, specified in
     references/structure.md. `## Cover letter`.
   - A verbatim-clause attachment: source text reproduced word for word,
     tabbed so the reader finds one item, references/skeletons.md.
     `## Attachment: <name>`. Several attachments pass.
   An item under any other heading fails this check. A cover letter sits
   before the body, not after it: it is front matter, not end matter, and
   scripts/check-report.sh scans from the first end-of-body heading (Sources,
   Deviations, Format elements, or an Attachment) to EOF. A leading cover
   letter falls before that scan and is never inspected by the script; check
   11 stays a human read. [contract]
3. The title states the conclusion, and the subheads, read alone, carry the
   argument; each subhead states a sub-conclusion, not a topic. [contract,
   Part I, Part V]
4. The conclusion is not buried past the first paragraph. [Part V]
5. Exclusion scan against the exclusion list in SKILL.md, including the ban on
   stating an inference in the grammatical form of a fact.
   Where the report uses a format whose skeleton requires an excluded
   element, whoever chose that format, that element passes this check, and the
   report names every excluded element the format claimed, by their names on
   the exclusion list.
   All of them: the excluded elements each format claims are fixed by the
   format table in references/collisions.md, and the note names every
   element on that format's row. Announcing the format's parts is not naming
   them. That naming goes in the format-elements note, one end-matter item
   under the heading `## Format elements` (check 2), never in the notes file
   and never folded into the body. scripts/check-report.sh diffs the table
   row against the note. (The tie-break: references/collisions.md.)
   [Part I, Part III, ICD-D / `4b0f9a500133`]
6. Every number is compared to another number, and every figure carries its
   context. The reader never has to wonder good-or-bad. A number the report
   derives names the numbers it came from and their sources. A number that
   appears in no source and in no named derivation does not appear in the
   report. Naming the inputs is not explaining the calculation: in
   references/sample-reports.md the good report names them and the bad report
   explains them. (Comparison mandate: references/evidence.md.)
   [Part II, Part V]
7. No vague evaluative terms: "significant," "appear," and their kin.
   (Weasel list and the sentence layer: references/style.md.) [Part V]
8. Every graph has a thesis, stated in its title, with labels complete.
   (Graph rules: references/evidence.md.) [Part II]
9. Sources are precise, varied in kind, weighed for credibility, and listed
   at the end. (Source credibility and the citation template:
   references/evidence.md.) [Part III, Part V]
10. Competing claims are each addressed individually. [Part V]
11. External report: the cover letter is present, purpose first, with the
    expected response explicit. (Cover letter and the paper formats:
    references/structure.md.) [Part IV, Part V]
12. Connective sweep done; read-aloud pass done; spell-checker blind spots
    checked; pause before send. (These fold into the three-pass edit below;
    the sentence-connective sweep and the weasel scan live in
    references/style.md.) [Part II, Part IV]
13. Every major judgment carries a likelihood term from one declared ladder.
    No sentence mixes ladders, and no sentence pairs confidence with
    likelihood. A judgment that is not empirical carries no band: a value
    commitment, a legal disqualification, or a policy rule states its premise
    as a premise and names where the premise comes from. A band on a value
    claim fails this check. (The published ladder: references/style.md.)
    [ICD-D / `4b0f9a500133`]
14. No weasels: scan for "serious possibility," any modified "possible,"
    "may well," and bare "reportedly." (Full weasel list:
    references/style.md.) [WEP-weasel / `aeb42b8d8272`, WEP-poss /
    `cd13aa254952`]
15. Assumptions are marked as assumptions, and each states what follows if it
    is wrong. [ICD-D / `4b0f9a500133`]
16. Where options were compared: the criteria, the weights with their
    rationale, and both matrix totals are present, and the result is
    summarized in the body. (Criteria, weights, and the decision matrix:
    references/recommendation.md.) [FM-s3 / `8725de6c1699` for the criteria and
    weights, FM-comp / `2c2057b2b0bc` for the unweighted and weighted totals,
    FM-s6 / `79c5593207c0` for the body summary]
17. The recommendation commits to one course, and the decision-maker's job is
    to approve or disapprove, nothing more. Where no option passed screening,
    the report says so and names what would have to change for one to pass,
    rather than recommending a screened-out option. (The screening gate:
    references/recommendation.md.) [TQ-17 / `998664c6e1ca`]
18. The key assumptions check ran twice, at the start of the work and again
    before finalizing, and both outputs are recorded. The sensitivity test ran
    and its output is recorded: for each critical item of evidence, what
    breaks if that item is wrong. Any single point of failure it found is
    named in the report. [TP-KAC / `7e153dcfe3f3`, TP-ACH / `cbb733100aa5`]
19. The edit ran in three passes, in order: big picture, then paragraphs,
    then sentences and words. [TQ-8 / `53e9088f329b`]
20. Contrary information and the losing options are acknowledged, not omitted.
    A source's position is stated as the source stated it. Do not add a
    qualifier the source did not use, and do not drop the sentence that closes
    the option. [ICD-D / `4b0f9a500133`, TP-ACH / `cbb733100aa5`]
21. Every major judgment names its falsifier, the condition or the information
    that would change it. A judgment with no stated falsifier is not finished.
    A judgment that is not empirical names instead what would have to change
    for it to stop holding: the premise, the policy, or the finding it rests
    on. A falsifier that restates the reasoning is not a falsifier.
    [contract, ICD-D / `4b0f9a500133`]
22. No session context, chat log, or raw source text is pasted into the
    report; every fact appears as transformed notes with its source recorded.
    The step 3 notes exist as their own file beside the report, named
    `<report-name>.notes.md`, and every fact in the report traces to a line in
    it that names the source. No notes file is a fail. The remedy is
    returning to step 3 and writing the notes from the sources; a notes file
    written by copying facts back out of the finished report still fails this
    check, since it proves nothing about what the draft was built from. A
    criterion, a weight, or a matrix cell traces to a notes line whose source
    is the analysis handover, the same way a fact traces to the document it
    came from. One that traces to no such line was manufactured while
    drafting, and it fails this check. The remedy is the send-back in step 5,
    never a line added to the notes to cover it.
    scripts/check-report.sh walks the materials directory the operator
    named, recursively, for a 40-plus-word span that also appears in the
    report or in its notes file, whitespace and case normalized, and fails
    unless this check is scored `not-met` with the deviation recorded. The
    notes file is scanned like any other: a clause that reaches the report
    by way of the notes is still untransformed source text. Matching
    tolerates small insertions, so padding a paste with `[sic]` does not
    hide it. A file the scan cannot read, a PDF among them, is named and
    fails the run; it is never passed over in silence, because a clean
    result over material nobody compared is a false one. Extract such a
    file's text beside it and run again. An operator instruction can
    authorise the paste; it cannot excuse recording it, and a verbatim
    clause under an `## Attachment:` heading gets no exemption from that.
    (The notes discipline is step 3.) [contract, Part III]
23. Every check this report does not meet appears in the deviations block as
    its own entry, with its authorising rule quoted and what the reader loses.
    Score every check on the scoreboard first, then transcribe.
    scripts/check-report.sh counts the not-met rows, counts the entries, and
    fails when they differ or when a row's quoted rule does not appear in its
    entry. An entry with no quoted authoriser fails this check. This check
    records what you already found; a check you scored met
    that the report does not meet is caught by a second reader, not here. This
    check does not apply to itself: a missed deviation record needs no
    deviation record of its own, or the check could never close. Where every
    other check on this list passes, there is nothing to record; leave the
    deviations block out of the report, and an absent block is what a clean
    report looks like, not a fail. [contract]

## Key assumptions check (run twice)

Report presumes an answer before you finish it. This check drags every premise
that answer rests on into the open. Run once at step 1, against the answer the
assignment already presumes, and once here at step 8, against the finished
draft. Record both outputs; check 18 verifies they exist.
[TP-KAC / `7e153dcfe3f3`]

Each run, in order:

1. Write down the current line, the answer as it stands.
2. Articulate every premise the line needs to be valid, stated and unstated.
   The unstated ones are where the report hides.
3. Challenge each premise: why must it be true, and does it hold under all
   conditions.
4. Keep only the premises that must be true. Discard the rest.
5. For each premise you kept, name the conditions or the information under
   which it would fail.

Step-1 run shapes the work. Step-8 run confirms the finished draft did not
quietly acquire a premise that will not hold. A premise surviving both runs
but still able to fail is an assumption: mark it as one and state what follows
if it is wrong (check 15).

## Sensitivity test (every report)

Run on every report, right after the second key assumptions check.
[TP-ACH / `cbb733100aa5`]

1. Name the few critical items of evidence the conclusion leans on hardest.
2. For each, ask: if this item turned out wrong or misleading, what breaks.
3. Write down what breaks. If the whole conclusion breaks on one item, that
   item is a single point of failure; say so in the report and treat the
   item's own reliability as load-bearing.

Output is a short list of "if X is wrong, Y breaks" lines. Record it.

## The three-pass edit (in order)

Edit in three passes, in this order, never all at once. Each pass has its own
eye; mixing them means you polish a sentence in a paragraph you were about to
cut. [TQ-8 / `53e9088f329b`]

**Pass 1, big picture.** Task, purpose, introduction, conclusion, overall
length, relevance, completeness. Does the draft answer the assignment; is
anything in it that does not serve the answer; is anything missing.

**Pass 2, paragraphs.** Unity of focus, topic sentences, supporting ideas,
transitions. Each paragraph makes one point and opens by saying it. Connective
sweep runs here: check the places a paragraph turns, gives an example, or adds
to a list, and confirm a tagword tells the reader what comes next.

**Pass 3, sentences and words.** Passive voice, unclear language, wordiness,
grammar, spelling. Read-aloud pass runs here (read it aloud, or have it read
to you), and the spell-checker's blind spots, words it passes but the sentence
misuses (then/than, affect/effect).

Then the pause before send: review the whole thing once more, confirm it is
what you meant to send.

To slow a pass down on purpose: read aloud, read one line at a time under a
cover, or read the sentences backwards.

## The structured challenge: what runs always, what runs on request

Challenge material splits two ways. Hold the split; never promote a heavy
technique to a default.

**Cheap, always.** The key assumptions check (both runs) and the sensitivity
test run on every report, no exceptions. That is the whole structured
challenge for an ordinary report.

**Heavy, on request only.** Analysis of competing hypotheses, Team A and
Team B, devil's advocacy, and red team are heavy techniques. Run one only
when the operator asks for it by name. Never trigger one as an agent default,
and never let an uncomfortable conclusion talk you into one on your own.

What each heavy technique is: references/challenge-heavy.md. Load only when
the operator names one.
