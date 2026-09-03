# Options, and analyzing each one alone

Steps 6 and 7. Criteria frozen before this file opens. If not, go back.

## At least two genuinely distinct options

One option is not a recommendation: nothing was compared.

Distinct means a competent person would actually consider both. Two variants of
the same course with different numbers are one option. Record, per option, one
line saying what makes it different in kind from the others.

**Do not manufacture a second option to satisfy the count.** One real option
plus one straw option -> winner that beat nothing, same defect
comparing-while-analyzing produces, arrived at from the other direction. Tell
in the finished matrix: an option scoring worst on every criterion.

### The single-option defense

Second real option does not exist: write the defense instead of inventing one.
The defense states what alternatives were considered and why each is not
available: foreclosed by a constraint, already tried and failed, or outside the
authority of the deciding party.

Then say the decision matrix does not apply, and hand over the defense in its
place. Defended single option is admissible. Undefended one is a recommendation
with no comparison behind it.

## Building options when nobody handed you any

Take the two forces both most critical to the outcome and most uncertain. Give
each two opposed endpoints. Cross them into a four-cell grid, one option per
cell.

```
                    Demand grows        Demand flattens
Costs rise          Option A            Option B
Costs hold          Option C            Option D
```

Some cells produce nothing usable. That is a result. Say which cell was empty
and why rather than padding it.

Grid is a generator, not an analysis. Four cells still go through the screening
gate like anything else.

## The screening gate

Run the five screening criteria as pass or fail, before any scoring. Record a
verdict and a reason per option.

```
Option              Screen verdict   Reason
A. In-region cold   pass             All five met
B. Offshore archive fail             Suitable: breaches the DPA at C2
C. Status quo       pass             All five met
```

Option failing one is out. Handover says which criterion it failed and why,
rather than scoring it low and keeping it in the matrix. Failing options are
still handed over, in section 6, as part of the record of what was considered.

## Step 7: analyze each option alone

Measure every surviving option against each criterion's benchmark on its own
merits. Do not compare options here. Comparing while analyzing tempts you
toward the answer you already like, and it hides the case where every option
fails.

Concrete: measure option A against the 4-hour restore benchmark, write what it
does. Do not write down that A restores faster than B. That sentence belongs
at step 8.

```
Option A, in-region cold storage
  Compliance posture   High. Meets the DPA and the retention schedule.
  Monthly cost         $8,400 against a $340k annual line. Within C1.
  Restore time         6.5 hours against a 4-hour benchmark. Over.
```

Facts surfacing here go into the fact notes. Step 5 freeze covers criteria,
not evidence.

### Escalation methods fire here

Step 3 routed to risk, causation, probability, or cost: those methods run
inside the per-option analysis rather than beside it. Load the one file that
fired, references/method-risk.md, references/method-root-cause.md,
references/method-causal-claims.md, or references/method-cost.md. Record which
ran and which trigger fired.

### Test against the alternative futures

Option grid produced futures, or the environment named conditions that could
shift: test each option against every future in turn. Say which futures it
survives and which one breaks it. Prefer an option holding across all of them,
and say so explicitly when one does.

Option winning on the criteria but surviving only one future is a finding, not
a winner. Carry it to step 8 with the fragility attached.

### The second-order pass

Applied to the option you will recommend, at step 8, not to every option here.

Two moves. Per actor in the frame, name what changes for them once the course
is taken. Per item on the constraints list, say whether the course consumes it,
leaving less room for the next decision.

Name at least one concrete change per affected actor. Restating the actor list
with no change attached is this pass's failure mode.

## Hands forward

Sections 6, 7. Section 7 also carries the alternative-futures result and any
escalation-method output.
