---
name: create-report
description: >-
  Draft a standalone report for a reader who is not the operator and was
  not in the working session: a decision-maker, a client, or a reviewer who
  will read the report alone. Fires whenever the deliverable is a report,
  memo, position paper, background paper, or staff study that must carry its
  own conclusion, evidence, and stated uncertainty to that reader. Not for
  notes you keep for yourself, and not for prose written back to the operator.
---

## Meta-rule

Operator instructions for this report outrank every rule in this skill.
Operator instruction differs from anything below -> instruction wins.
Following instruction against a rule here is a deviation, and the report
records it. Record shape: references/checklist.md.

## Scope: this skill drafts, it does not analyze

Analysis is work already done. Steps below turn that work into a report. Step
naming an analysis procedure (key assumptions check, criteria and decision
matrix, evidence tests) names a standard the finished work must meet and
record, never a fresh task to run.

## The report contract

Every run meets all of these.

- The written-out question governs the report.
- The thesis and main conclusion appear in the first paragraph, with the
  primary supporting reasons grouped into categories, not a flat list.
- The first paragraph announces the order; the body follows it exactly.
- The body contains only what the first paragraph promises.
- Every container announces its point in its own label. The title states the
  conclusion, each subhead states its sub-conclusion, each paragraph opens by
  saying its point, and each graph is titled with its thesis. (This four-level
  container law is a synthesis across four of Daniel's rules, marked as such.
  No single page states it.)
- Say nothing that is not part of the answer to the question asked.
- Every claim carries specific support, every number is compared to another
  number, and every source is listed.

Four more clauses, in the contract's own voice:

- Every major judgment states its likelihood on the ladder the report
  publishes, and states confidence in the judgment separately. Likelihood and
  confidence never share a sentence. A judgment that is not empirical carries
  no band; it states its premise as a premise and names where the premise
  comes from.
- Assumptions are marked as assumptions and never presented as information.
  Each critical assumption states what follows if it is wrong.
- Where a recommendation is asked for and the analysis compared options, at
  least two genuinely distinct options were compared against criteria set
  before the options were generated. Where the analysis instead states that no
  matrix applies and gives its reason, a defended single option, a screening
  that emptied the field, or a question of fact, this clause is met and the
  report owes no deviation entry. A single option handed over with no such
  reason is not a recommendation, because nothing was compared.
- Every major judgment names what would change it. A judgment with no stated
  falsifier is not finished. A judgment that is not empirical names instead
  what would have to change for it to stop holding.

Design mark on those four: ICD 203 writes several as "should" and "as
appropriate". Contract states them as musts. Skill design decision, not source
wording.

Report prints the ladder it uses. Ladder table: references/style.md.

Contract is also the revision rule. Any revision leaves the first paragraph's
promise true: new material merges into the announced structure, or the
announcement changes with it.

## Do not include

Directly under the contract. Non-negotiable. Do not restate the problem; do
not announce that the research was completed; do not summarize background; do
not define terms; do not explain calculations; and do not footnote your own
conclusions, presentation explanations, or summaries.

One more, at the register layer: do not state an inference in the grammatical
form of a fact. Underlying information, assumptions, and judgments stay
visibly distinct.

## The eight steps

1. **Assignment.** Write out the specific question the report answers before
   anything else. Topic is the question; thesis is the answer. Yes-or-no asked
   means yes-or-no answered. "Look into X" is not an assignment. One
   controlling purpose governs, and every sentence serves it. Where the
   question came from someone else, get the problem statement approved before
   working on it, cast as who, what, when, why, and how. Run the key
   assumptions check here, against the answer the assignment already presumes.
   It runs twice: here and at step 8.
2. **Audience.** Set two dials together: omit as much as possible (what the
   reader already knows) and be as technical as possible (what the reader can
   absorb). Default reader: intelligent, suspicious, busy. Address four roles,
   not one reader: primary receivers, secondary receivers, key decision
   makers, and gatekeepers.
3. **Notes.** Collect the facts the report will use in their own file beside
   the report, named `<report-name>.notes.md`. Transform each idea into your
   own words rather than copying text, and record each fact with its source.
   This is the counter to pasting session context into the report. Check 22
   fails when the file is not there.
4. **Thesis.** Form it from the notes, after them, never as a starting
   assumption. State it with its primary supporting reasons grouped into major
   categories.
5. **Plan.** Build a skeleton plan (the order of arguments), then a final plan
   that correlates every note with the point it supports. No prose yet. A note
   supporting no point gets cut here, which enforces the exclusion rules before
   drafting. Where the report recommends, this step lays out the criteria and
   the decision matrix the analysis already used; both are standards that
   analysis must have met, not work to do here. Analysis that arrives stating
   the matrix does not apply, with its reason, a defended single option, a
   screening that emptied the field, or a question of fact, has met the
   standard: draft from what it handed over. Analysis that owed a matrix and
   arrives without one has a gap this skill cannot close: say so and send it
   back. Writing a criterion, setting a weight, or building a matrix at this
   step is doing the analysis, which this skill never does. Two moves are
   compliant here and there is no third: send the work back, or draft from
   what was handed over.
6. **Draft.** Largely mechanical if step 5 was honest. Apply the exclusion
   list, the evidence rules, the sentence layer, and the uncertainty layer.
7. **Revise.** Read the draft aloud, or have it read to you. Run the
   connective sweep: references/style.md. Check the words a spell-checker
   passes but the sentence misuses. Pause before you send. Three passes, in
   order: big picture, then paragraphs, then sentences and words.
8. **Check.** Run references/checklist.md against the finished draft. Score
   every check on `<report-name>.checks.md` beside the report, then run
   `bash <this-skill-directory>/scripts/check-report.sh <report>
   <materials-dir>`, passing the folder the operator named, and fix what
   it names. Run the key assumptions check a second time and run the
   sensitivity test; record both outputs. The heavy challenge techniques
   (competing hypotheses, Team A and Team B, devil's advocacy, red team) run
   only when the operator asks for them, never as your default.

## Collisions

Five rulings an agent otherwise gets wrong: data plural, hedging versus
calibration, conclusion-first versus hostile reader, analysis order versus
presentation order, named format versus exclusion list.
references/collisions.md. Load when two rules here appear to conflict, or
when the report uses a named paper format, whoever chose it.

## Failure modes

Four named ways an agent-drafted report fails.

- Context bleed. Session context or source text pasted into report, not
  transformed notes.
- Agent narration. Report announces own process: restated problem, research
  announcement, explained calculations, footnoted own conclusions.
- Revision as append. New material bolted on the end, not merged into the
  announced structure -> first paragraph's promise broken.
- False confidence. Inference stated in the register of a fact, or conclusion
  given with no stated likelihood or confidence.

## Pick the format from the function

Pick one shape from the function it serves. Hold it fixed whole report. Detail
and skeletons: references/structure.md.

- Point paper: one-page bullet brief, quick reference or decision now.
- Talking paper: bullet talking points to carry into discussion or briefing.
- Bullet background paper: background in bullets, reader needs facts fast.
- Background paper: same background in prose, reader needs the reasoning.
- Position paper: argues one position, asks reader to adopt it.
- Staff study: full problem-to-recommendation report, five-part body.

## Reference files

Load on demand. Each is this skill's own file.

- references/planning.md. Steps 1 to 5: assignment, audience, notes, thesis,
  plan. Load when working steps 1 to 5.
- references/recommendation.md. Criteria, screening and evaluation, weights,
  decision matrix, committing to one course. Load when report recommends among
  options.
- references/structure.md. Organization pattern, paragraph template, cover
  letter, paper formats above. Load when choosing a shape or building the
  skeleton.
- references/skeletons.md. Staff-study five-part body and running-estimate
  format, verbatim. Load when the report is a staff study or a running
  estimate, whoever chose it.
- references/style.md. Sentence layer, numbers rules, likelihood ladder,
  weasel list. Load when drafting or revising sentences, or stating
  uncertainty.
- references/evidence.md. Comparison mandate, graphs, footnote policy, source
  credibility, argument tests. Load when placing numbers, graphs, or sources.
- references/checklist.md. Step 8 checks, key assumptions check, three-pass
  edit, structured challenge. Load at step 8 before finalizing.
- references/collisions.md. Five tie-breaks. Load when two rules appear to
  conflict.
- references/challenge-heavy.md. Four heavy techniques. Load only when the
  operator names one.
- references/sample-reports.md. One bad report, one good rewrite, annotated.
  Load when you want a worked example of the contract.
