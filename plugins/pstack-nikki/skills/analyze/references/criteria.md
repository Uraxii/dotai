# Criteria

Step 5. Runs before any option exists.

Two kinds, in order. Screening first, then evaluation.

## Screening criteria: is the option admissible at all

These define the limits of an acceptable solution. Option may be rejected on
these alone, and rejection is a pass or fail verdict, never a low score.

Five categories.

- **Feasible.** Fits within available resources.
- **Acceptable.** Worth the cost or the risk.
- **Suitable.** Solves the problem, and is legal and ethical.
- **Distinguishable.** Differs significantly from the other options.
- **Complete.** Contains the critical parts of solving the problem, start to
  finish.

Write each as a specific test against this problem's constraints list, not as
the category word. "Feasible" is a heading. "Fits inside the $340k FY26 infra
line at C1" is a criterion.

### Whose standard settles acceptable and suitable

Judge against guidance issued by the authorizing party, not against your own
judgment. That is the sourced answer, and it covers only one side.

Authorizing party issued no such guidance: do three things, do all three.

1. Name the absence in the handover. Do not let silence read as compliance.
2. Write down the standard you actually used.
3. Mark it as your own.

Objectives of the stakeholders a decision lands on are recorded from the actor
table and listed alongside the screening verdict. Never folded into it. Nothing
in the sourced material names a standard-setter on that side, and merging their
objectives into your verdict invents one.

## Evaluation criteria: separate the survivors

A well-formed evaluation criterion has five parts. All five.

- **Short title.** The criterion's name.
- **Definition.** A clear description of the feature being evaluated.
- **Unit of measure.** A standard element that quantifies it. Dollars, hours,
  incidents per quarter.
- **Benchmark.** A value defining the desired state, what "good" means for this
  criterion.
- **Formula.** How a change in the value changes desirability, stated in
  comparative terms ("less is better") or absolute terms ("in-region beats
  out-of-region").

Criterion missing any of the five is an opinion wearing a label. "Cost" with
no unit, no benchmark and no direction is not a criterion. It is a place to
hide a preference.

Worked example, one criterion in full.

```
Short title:      Restore time
Definition:       Wall-clock hours to restore the full archive from cold
Unit of measure:  Hours
Benchmark:        4 hours, the RTO in the DR policy
Formula:          Under 4 an advantage, over 4 a disadvantage. Less is better.
```

Set the benchmark by reasoning, by historical precedent, or from a current
example. Averaging the options is the worst way: it duplicates the comparison
you have not run yet and guarantees somebody passes.

Benchmark landing exactly on one option's value is the signature of a
retrofitted criterion. Happens honestly -> say why.

## Direction, before any score

State per criterion whether it is minimized or maximized before computing
anything. Which end of the scale counts as better is fixed up front, not
inferred from the numbers once they arrive.

## Normalization, before any score

Criteria measured on different scales or in different units are normalized to
one common scale before combining. Dollars, hours and a satisfaction band
cannot be added.

Criterion uses qualitative bands: define every band with an explicit numeric
threshold before scoring anything.

```
Compliance posture
  High   (3)  Meets the DPA and the retention schedule with no exception
  Medium (2)  Meets the DPA, needs a documented retention exception
  Low    (1)  Requires a DPA amendment
```

Bands assigned after the options are in front of you are not bands. They are
the ranking you already had, written backwards.

Cross-unit normalization has no method behind it here beyond the requirement to
fix thresholds first. Say which scheme you used and that you chose it.

## Mandatory criteria

Mark any criterion that is a hard requirement rather than a preference. A
mandatory criterion gates inside the matrix, not only at the screening stage:
an option that fails one is dropped from the matrix entirely, never down-scored
and kept in.

Only structural guard against a high score on one criterion hiding a failing
score on another. Works at the floor and nowhere above it.

Record the drop with the criterion it failed. Silent drop and rescued
favourite are indistinguishable in the output.

## Weights

Criteria almost never equally important. Weight them so weights sum to 100
percent, and state one line of rationale per weight.

Rationale matters more than the numbers. Reader can argue with "compliance
carries 40 percent because a DPA breach ends the contract". Nobody can argue
with a column of unexplained percentages.

Operator gave a weighting instruction in words: quote it as the rationale's
source rather than paraphrasing it into a number silently.

```
Criterion            Weight  Rationale
Compliance posture   40%     Operator: compliance matters more than money
Monthly cost         35%     Bounded by C1, the FY26 infra line
Restore time         25%     DR policy sets an RTO but tolerates overrun
```

## Freeze

Set closes here. Takes no new member once options are on the table. Adding a
criterion mid-analysis is how a preferred option gets rescued, and it is the
failure this whole step is ordered to prevent.

Record the freeze point in the handover. Freeze binds criteria only; fact
notes stay open through step 7.

### When the options arrived first

Operators hand over named options all the time. The ordering this step demands
is then already broken by the input, and pretending otherwise produces criteria
reverse-engineered from a comparison sheet.

Do this instead. Derive the criteria from the problem frame and the constraints
list, working from step 2's output and not from the option material. Then
freeze. Then look at the options. Then say in the handover that the options
arrived before the criteria and what you did about it.

Naming the violation is worth as much as avoiding it, and it is the only signal
a downstream reader has that the criteria were not fitted.

## Hands forward

Section 5.
