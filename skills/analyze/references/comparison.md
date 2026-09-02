# Comparison, commitment, and the handover

Step 8. Every option has already been measured alone. Nothing new joins the
criteria set here.

## The decision matrix

Options across, criteria down, a rank or score per cell, and both totals shown.

```
Criterion (weight):   Compliance(40) Cost(35) Restore(25)
Option A rank:        1 (40)         2 (70)   2 (50)
Option C rank:        2 (80)         1 (35)   1 (25)

Option A total:  5 unweighted, 160 weighted
Option C total:  4 unweighted, 140 weighted
```

Rank each option per criterion, lower rank preferred. Add the ranks across for
the unweighted total. Multiply each rank by its criterion's weight and add
those across for the weighted total. Show both.

The weighted total is plain arithmetic, multiply and sum. It is stated here as
arithmetic and nothing more. No method behind it decides what a correct weight
is, what a correct scale is, or what to do when the arithmetic misbehaves. The
three ways it misbehaves are named at the end of this file.

The matrix is where the decision starts, not where it ends. Say in the text
where the judgment was subjective. Comparing option by option on one criterion
is often more useful to a reader than comparing two totals.

## The weight re-run

Re-score the matrix under plausibly different weights and record whether the
ranking held. This is a required step, not an optional check, and it is
distinct from the evidence-sensitivity test and from cost sensitivity.

"Plausibly different" means a weighting a reasonable person could have argued
for at step 5, not a weighting reverse-engineered to flip the answer. Move the
largest weight and the smallest, one at a time.

Record the result either way.

```
Weight re-run
  Compliance 40 -> 30, Cost 35 -> 45:  ranking held, C ahead
  Compliance 40 -> 55, Cost 35 -> 25:  ranking flipped, A ahead
```

A ranking that flips under a defensible reweighting is a close call. Go to the
close-call clause below.

## The option-set check

Drop each non-winning option from the matrix in turn and recompute. If the
ranking of the remaining options changes, say so in the handover.

This is here because the arithmetic has no guard against it and because
nothing else in the procedure would surface it. A recommendation that depends
on which losing options happened to be in the field is a fragile
recommendation, and the reader is entitled to know.

## Breaking a tie

Where two options finish level on the weighted total, break it on the
criteria, not on a fresh overall judgment. In order:

1. The higher-weighted criterion where they differ.
2. Which option survives more of the alternative futures.
3. Which option consumes fewer of the constraints, leaving more room for the
   next decision.

This ordering is a design decision. No source supplies a tie-break for options
on a decision matrix. Label it as such where you use it.

## Commit to one course

Having compared, commit. Recommend one course and make the decision-maker's
job approval or disapproval, nothing more. Answers, not questions.

"Recommend further study" and "either A or B" both hand the decision back.
Neither is a recommendation.

Two shapes this rule is often misread as forbidding, and does not.

**The package.** An ill-structured problem may need several measures applied
together or in sequence. That package is one course. Name it as one, order its
parts, say which part comes first and what triggers the next. The
decision-maker approves the package. Four independent recommendations is a
menu; a sequenced package is a course.

**The close call.** Where the leading totals sit inside the noise, or the
weight re-run flipped the ranking, still name one. Then, in the same breath:

- State that the margin is inside the noise. Do not present a coin-flip as a
  clear win.
- Name the observable that would break the tie. An observable, not "more
  analysis". "Their Q4 incident postmortem, if it shows more than two Sev-1s"
  is a tie-breaker. "Further investigation" is not.
- Hand the runner-up over alongside, with what it would take to prefer it.

Never hand over an unresolved pair. Disclosure is the concession, not
abstention.

## What still goes over with it

- **Surviving disagreement.** Where a real disagreement outlasted the
  comparison, name it and put it in front of the decision-maker rather than
  smoothing it away. Committing to one course is not the same as hiding that
  the call was close or contested.
- **The losing options.** With their scores and why they lost.
- **The contrary evidence.** Everything found that cuts against the
  recommendation, from the fact notes. Showing only what supports the answer is
  stacked evidence, and it is the failure that is hardest to detect from
  outside.

## The matrix result in prose

Write the matrix result as a paragraph a reader can act on without opening the
table: which option won, by what margin, on which criteria, and where the
judgment was subjective. A reader who has to reconstruct the answer from a
grid has been handed homework.

## Closing the run

Three things before the handover goes out.

1. Run the key assumptions check a second time, now against the answer you
   reached rather than the one the question presumed. Record the output
   alongside the first run.
2. Run the evidence-sensitivity test. Name the evidence the conclusion leans
   on hardest and what breaks if each item is wrong. Record it.
3. Write the thesis: one sentence, the answer to the question as asked. It is
   written now, after the fact notes and after the comparison, never earlier.
   A thesis fixed at the start and supported afterwards is the failure the
   whole ordering exists to prevent.

Then assemble handover sections 1 to 11. Section 12 fills at step 9, as the
gate runs. Where a section does not apply, say which and why. A section that
is quietly absent and a section that does not apply look identical from
outside, and only one of them is acceptable.

## Where the arithmetic misbehaves

Three known pathologies. Named because none of them has a method here.

- **Rank reversal.** Adding or removing an option changes the ranking of the
  others. No guard exists. The option-set check above surfaces it; disclosure
  is the whole response.
- **Compensability.** A high score on one criterion offsets a failing score on
  another, and the total hides it. Guarded only at the floor, by the mandatory
  criterion gate. Above that floor, an option can be quietly terrible at one
  thing and still win.
- **Normalization across unlike units.** Constrained only by fixing numeric
  thresholds before scoring. The choice of scheme is yours and should be
  stated as yours.

Rounding and significant figures have no standard behind them either. Carry
the precision of the least precise input and say that is what you did.

## What step 8 hands forward

Handover section 8: the matrix, both totals, the weight re-run result, and the
option-set check. Section 11 in full. Sections 9 and 10 close here.
