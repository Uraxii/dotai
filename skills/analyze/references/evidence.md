# Evidence and uncertainty

Step 4, plus the uncertainty layer every later step uses. Load at step 4 and
keep it open.

## Fact notes

One artifact, one row per fact, built before any answer is formed. A thesis
fixed first and supported afterwards has inverted the process, and the output
looks identical to the honest version.

```
Fact                                  Source              Kind
Onboarding completion 14% in Q1       accounts_2026q1.csv fact
Pricing drove the churn               cs_lead_note.md     judgment
Renewal terms hold through FY27       renewal_terms.md    assumption
```

Three rules on the rows.

- Write each one in your own words. Copying source text into the note carries
  the source's framing forward and defeats the whole artifact.
- One source per fact, named specifically enough to reopen.
- Mark the kind. Fact, assumption, or judgment. A judgment written in the
  grammatical form of a fact is the single most expensive error in the
  handover, because nothing downstream can detect it.

The table stays open through step 7. Facts surface while options are being
measured, and they belong here, not in a second list. The freeze at step 5
binds criteria, not evidence.

Do not drop a factor because it cannot be counted. Name the variables that
resist measurement and assess their likely effect on the outcome from facts
and stated assumptions. An unmeasurable factor left out of the notes is a
factor the decision silently assumes is zero.

Record what cuts against the emerging answer as you find it. Contrary evidence
collected at the end is contrary evidence you went looking for after you had
already decided, and it will be thinner than the supporting set for reasons
that have nothing to do with the world.

## Source assessment

One row per source. This is where a source's weakness gets attached to the
judgments that rest on it, which is the only place it can still change
anything.

```
Source        What it is       Strengths       Weaknesses        Carries
accounts.csv  Billing export   Complete, dated No usage data     J1, J3
cs_lead.md    One lead's note  Close to users  Never opened the  J2
                                               billing export
```

Judge a source by whether it discriminates, not by whether it agrees. Evidence
that fits the leading answer but fits the alternatives equally well is worth
nothing and should be dropped from the reasoning even though it feels
supportive.

Give little weight to a single anecdote or case unless it is known to be
typical. Prefer aggregate data where it exists.

Do not fully accept or fully reject a source of uncertain reliability. Carry
the uncertainty through into the combined judgment.

## Assumptions register

```
Assumption                    Why held             If wrong      Critical
Renewal price holds at list   Contract clause 4.2  Cost flips    yes
Headcount flat through FY26   Verbal, unconfirmed  Timeline slip yes
```

Every assumption states what follows if it is wrong. Critical ones marked. An
assumption with no consequence written next to it has not been examined; it
has been noticed.

## The key assumptions check

Runs twice. Once at step 4, against the answer the question already presumes,
before the analysis hardens. Once at step 8, against the answer you reached.
Record both outputs. The first run is the valuable one and the easiest to skip,
because at step 4 there is nothing yet to check it against except your own
priors, which is exactly the point.

Each run asks, of every premise the analysis rests on:

- Would this still hold if the situation changed in the ways it plausibly
  could?
- What evidence would show it is already false?
- Who would disagree with it, and on what basis?

A premise that survives both runs but could still fail is an assumption, and
it belongs in the register above rather than in the fact notes.

## The evidence-sensitivity test

Runs once, at step 8. Distinct from the weight re-run in comparison.md and
from cost sensitivity in methods.md. Naming them apart is not pedantry: an
agent that runs the weight re-run and calls the evidence-sensitivity test done
has shipped an incomplete handover that looks complete.

Name the few items of evidence the conclusion leans on hardest. For each, write
what breaks if it turns out to be wrong, and whether the recommendation
survives. Record the output. Where the recommendation does not survive the
loss of one item, say so plainly; that is the most useful sentence in the
handover.

## Deriving a probability

Runs when step 3 routed here, which is when the answer will carry a stated
likelihood. Not every question needs it.

- Start from the base rate of a comparable class of past cases, then combine it
  with case-specific evidence. Do not drop the base rate because the
  case-specific evidence feels compelling. It always feels compelling.
- Revising a running estimate, periodically discard the previous number and
  re-derive from scratch. Nudging a prior figure preserves whatever was wrong
  with it.
- Where the judgment depends on a chain of prerequisite events, multiply the
  individual probabilities. Do not average them.
- Before treating an easily recalled example as evidence of high frequency,
  check whether you recalled it for its vividness, recency, or personal
  relevance. Discount it if so.
- Where a tactical indicator conflicts with a standing strategic assumption,
  weight the indicator and treat the conflict as a reason to re-examine the
  assumption.
- Comparing hypotheses, select the one with the fewest inconsistencies against
  the evidence, not the one with the most supporting evidence. Supporting
  evidence accumulates on any hypothesis you spend time on.
- Where a variable relevant to the judgment is unknown, name it, weigh the
  values it plausibly holds, and lower the confidence. Do not assume a
  default.
- Before citing a correlation, check all four cells: both present, one
  present, the other present, neither. Confirming cases alone prove nothing.
- Reviewing a past judgment, reconstruct the original uncertainty by asking
  whether the opposite outcome would have surprised you at the time. Hindsight
  inflates remembered confidence.

Calibration over many judgments needs records that outlive one run, and
nothing here provides that. Do not claim calibration.

## Likelihood and confidence

Two different quantities, and they never share a sentence.

**Likelihood** is how probable the thing is. Publish the ladder you use at the
head of the judgment lines, words paired with numeric bands, so a reader who
distrusts one has the other.

```
Almost no chance   01 to 05 percent
Very unlikely      05 to 20 percent
Unlikely           20 to 45 percent
Roughly even       45 to 55 percent
Likely             55 to 80 percent
Very likely        80 to 95 percent
Almost certain     95 to 99 percent
```

**Confidence** is how much the evidence behind that number is worth: its
quality, its quantity, and how much of it discriminates. Cap confidence at low
where the judgment rests on a small body of evidence whose representativeness
cannot be determined, however internally consistent that evidence looks.
Internal consistency in a small sample is what a small sample does.

Empty hedging is banned and calibrated probability is required. "It would
appear costs may rise" is the banned half. "Costs are likely, 55 to 80
percent, to rise" is the required half.

## Falsifiers

Every major judgment names what would change it, and the falsifier names an
observable, not a feeling. "More analysis" is not a falsifier. "Completion
timestamps clustered at or after the churn dates" is.

A judgment with no stated falsifier is not finished.

## What step 4 hands forward

Handover sections 2, 3 and 4 in full. Section 9 opens here and closes at step
7. Section 10 gains the first key-assumptions-check output.
