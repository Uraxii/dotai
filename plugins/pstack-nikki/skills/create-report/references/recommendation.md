# The recommendation machinery

Load when the report recommends a course of action. Records what a sound
analysis must contain: at least two options, criteria fixed before the options,
per-option analysis, a decision matrix, one committed recommendation. Analysis
that did not do these has a gap, findable here before the report is written.

This file specifies standards. It does not analyze. Steps 1 to 5:
references/planning.md.

## At least two distinct options

One option is not a recommendation, because nothing was compared. Analysis
must have generated at least two genuinely distinct alternatives. A single
option is admissible only in the rare case where you can defend why no
alternative exists; stand ready to defend it (TQ-17 / `998664c6e1ca`).

## Set the criteria before the options, and freeze them

Criteria come before options and take no new member once analysis has started.
Adding a criterion mid-analysis is how a preferred option gets rescued.

Two kinds of criteria, in order: screening first, then evaluation.

## Screening criteria: is the option admissible at all

Screening criteria "define the limits of an acceptable solution"; an option may
be rejected on these alone (FM-s3 / `8725de6c1699`). Five categories, quoted
verbatim from FM 5-0:

- Feasible: fits within available resources.
- Acceptable: worth the cost or risk.
- Suitable: solves the problem and is legal and ethical.
- Distinguishable: differs significantly from other solutions.
- Complete: contains the critical aspects of solving the problem from start to
  finish.

Apply these as a pass/fail gate before any scoring. An option that fails one is
out, and the report says so rather than scoring it low and keeping it.

Every option can fail, and that is the finding. Do not soften a screen to keep
an option alive, do not present a screened-out option as the recommendation,
and do not supply a number that makes one look admissible. The qualifying
handover states that no option passed screening, names the screen each option
failed, and names what would have to change for one to pass. That statement is
the report's commitment, and it is not "recommend further study", which hands
the decision back. Screening that emptied the field but left a silent absence
with no such statement is a send-back per SKILL.md step 5.

## Evaluation criteria: differentiate the survivors

A well-formed evaluation criterion has five parts (FM-s3 / `8725de6c1699`,
FM-crit / `ef7984f51683`), verbatim:

- Short title: the criterion name.
- Definition: a clear description of the feature being evaluated.
- Unit of measure: a standard element used to quantify the criterion. Examples
  are U.S. dollars, miles per gallon, and feet.
- Benchmark: a value that defines the desired state or "good" for a solution in
  terms of a particular criterion.
- Formula: an expression of how changes in the value of the criterion affect
  the desirability of the solution, stated in comparative terms ("less is
  better") or absolute terms ("a night movement is better than a day
  movement").

Criterion missing any of the five is an opinion wearing a label. "Cost" with
no unit, no benchmark, no direction is not a criterion; it is a place to hide
a preference.

Worked example, one evaluation criterion in full (FM-s3 / `8725de6c1699`):

```
Short title:      Casualties
Definition:       Casualties taken during the entire operation
Unit of measure:  Number of casualties
Benchmark:        136 casualties
Formula:          Less than 136 is an advantage; greater than 136 is a
                  disadvantage. Less is better.
```

Set the benchmark by reasoning, historical precedent, or a current example.
Averaging is least preferred, because it "essentially duplicates the process of
comparison" (FM-s3 / `8725de6c1699`).

## Weight the criteria, and state each weight's rationale

Criteria are almost never of equal importance, so weight them. Rule that
matters: state the rationale for every weight, so the reader can challenge the
weighting rather than take it on faith. FM 5-0 (FM-crit / `ef7984f51683`):
"Regardless of the method used to assign criteria weights, leaders state the
rationale for each when recommending a solution to the decision maker."

## Analyze each option alone before comparing any

Analyze every option on its own merits first. Comparing while analyzing tempts
you to jump to the answer. FM 5-0 (FM-s5 / `a5bd6eef23dc`): "Comparing
solutions during analysis undermines the integrity of the process and tempts
problem solvers to jump to conclusions."

Measure each option against the benchmark alone before comparing, so the
analysis can report "all options fail on cost" instead of crowning a false
winner from a weak field.

Analytic order, and it does not conflict with putting the conclusion first in
the writing. Do the work in the analytic order; present it in the reader's
order.

## The decision matrix

Compare with a decision matrix: options across, criteria down, a rank per cell,
both unweighted and weighted totals shown. Worked example, adapted verbatim
from FM 5-0 (FM-s6 / `79c5593207c0`, lower total is preferred):

```
Criterion (weight):    Simplicity(1) Maneuver(2) Fires(1) Civil(1) Mass(2)
Option 1 rank:         2             2 (4)       2        1        1 (2)
Option 2 rank:         1             1 (2)       1        2        2 (4)

Option 1 total:  8 unweighted, 11 weighted
Option 2 total:  7 unweighted, 10 weighted
```

Read and build it (FM-s6 / `79c5593207c0`, FM-comp / `2c2057b2b0bc`): rank each
option per criterion, lower rank preferred. Add the unweighted ranks across
each row for the unweighted total. Multiply each rank by its criterion weight,
shown in parentheses, and add those across for the weighted total. Show both
totals; a weight of 1 needs no parenthetical.

Matrix is where the decision starts, not where it ends. FM 5-0 (FM-s6 /
`79c5593207c0`) on the quantitative techniques: "They are not the analysis and
comparison themselves." Say in the text where the judgment was subjective, and
that comparing option by option is often more useful than comparing totals.

Summarize the result in the body; reader learns the answer from the report, not
from an opened attachment. FM-s6 (`79c5593207c0`): the quantitative techniques
"should be summarized clearly so the reader need not refer to an attachment for
the results."

## Commit to one course

Having compared, commit. Recommend one course of action and make the
decision-maker's job approval or disapproval, nothing more. Completed staff
work: answers, not questions.

TQ-17 (`998664c6e1ca`): "The solution should be complete enough that the
decision maker has only to approve or disapprove." And: "your job is to advise
your boss what should be done, provide answers, not questions." And: "Do not
recommend alternatives."

Significant disagreement survives the comparison -> name it and put it in front
of the decision-maker rather than smoothing it away. Committing to one course
is not the same as hiding that the call was close. Losing options and contrary
evidence are acknowledged, not omitted; the check for that is in
references/checklist.md.

Sharpest wording of the recommendation itself, be absolutely clear what
response you expect, what steps, when, and by whom, is specified with the cover
letter in references/structure.md.
