# Options, and analyzing each one alone

Steps 6 and 7. The criteria are frozen before this file opens. If they are not,
go back.

## At least two genuinely distinct options

One option is not a recommendation, because nothing was compared.

Distinct means a competent person would actually consider both. Two variants
of the same course with different numbers are one option. Record, per option,
one line saying what makes it different in kind from the others.

**Do not manufacture a second option to satisfy the count.** A field of one
real option and one straw option produces a winner that beat nothing, which is
the same defect that comparing-while-analyzing produces, arrived at from the
other direction. The tell in the finished matrix is an option that scores
worst on every criterion.

### The single-option defense

Where a second real option does not exist, write the defense instead of
inventing one. The defense states what alternatives were considered and why
each is not available: foreclosed by a constraint, already tried and failed,
or outside the authority of the deciding party.

Then say the decision matrix does not apply, and hand over the defense in its
place. A defended single option is admissible. An undefended one is a
recommendation with no comparison behind it.

## Building options when nobody handed you any

Take the two forces that are both most critical to the outcome and most
uncertain. Give each two opposed endpoints. Cross them into a four-cell grid
and write one option per cell.

```
                    Demand grows        Demand flattens
Costs rise          Option A            Option B
Costs hold          Option C            Option D
```

Some cells produce nothing usable, and that is a result. Say which cell was
empty and why rather than padding it.

The grid is a generator, not an analysis. The four cells still go through the
screening gate like anything else.

## The screening gate

Run the five screening criteria as pass or fail, before any scoring. Record a
verdict and a reason per option.

```
Option              Screen verdict   Reason
A. In-region cold   pass             All five met
B. Offshore archive fail             Suitable: breaches the DPA at C2
C. Status quo       pass             All five met
```

An option that fails one is out. The handover says which criterion it failed
and why, rather than scoring it low and keeping it in the matrix. Failing
options are still handed over, in section 6, as part of the record of what was
considered.

## Step 7: analyze each option alone

Measure every surviving option against each criterion's benchmark on its own
merits. Do not compare options here. Comparing while analyzing tempts you
toward the answer you already like, and it hides the case where every option
fails.

The concrete difference: measure option A against the 4-hour restore benchmark
and write down what it does. Do not write down that A restores faster than B.
That sentence belongs at step 8.

```
Option A, in-region cold storage
  Compliance posture   High. Meets the DPA and the retention schedule.
  Monthly cost         $8,400 against a $340k annual line. Within C1.
  Restore time         6.5 hours against a 4-hour benchmark. Over.
```

Analyzing alone is what lets the handover say "all three options miss the
RTO", which a comparison alone can never say, because in a comparison
something always wins.

Facts that surface here go into the fact notes. The freeze at step 5 covers
criteria, not evidence.

### Escalation methods fire here

If step 3 routed to risk, causation, probability, or cost, those methods run
inside the per-option analysis rather than beside it. See methods.md. Record
which ran and which trigger fired.

### Test against the alternative futures

Where the option grid produced futures, or where the environment named
conditions that could shift, test each option against every future in turn.
Say which futures it survives and which one breaks it. Prefer an option that
holds across all of them, and say so explicitly when one does.

An option that wins on the criteria but survives only one future is a finding,
not a winner. Carry it to step 8 with the fragility attached.

### The second-order pass

Applied to the option you will recommend, at step 8, not to every option here.
It is a design decision with no source behind it and is not a general method
for second-order effects.

Two moves. For each actor in the frame, name what changes for them once the
course is taken. For each item on the constraints list, say whether the course
consumes it, leaving less room for the next decision.

Name at least one concrete change per affected actor. Restating the actor list
with no change attached is the failure mode this pass has.

## What steps 6 and 7 hand forward

Handover section 6: every option, its distinctness line, and its screening
verdict with the reason. Or the single-option defense.

Handover section 7: each surviving option against each criterion's benchmark,
measured alone, plus the alternative-futures result and any escalation-method
output.
