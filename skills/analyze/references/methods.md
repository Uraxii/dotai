# Escalation methods, and the four challenge techniques

Load only what step 3 routed to. Each block runs inside step 7's per-option
analysis, not beside it. Record which ran and which trigger fired.

## Risk rating and register

Fires when the question asks for a risk register or a risk rating.

Declare two things before rating anything, so the scale is fixed up front
rather than improvised per risk:

- The approach: quantitative, qualitative, or semi-quantitative.
- The orientation: threat-oriented, asset-oriented, or vulnerability-oriented.

Then rate on a five-band scale, Very Low to Very High, with each band anchored
to a numeric range.

1. Rate the likelihood the threat is initiated or occurs. For a deliberate
   threat, that is the actor's propensity. For an accidental one, it is stated
   frequency.
2. Separately, rate the likelihood that, given it occurs, it produces adverse
   impact.
3. Derive the overall likelihood by looking those two up in a fixed five by
   five table. Do not make a third fresh judgment.
4. Rate impact on the same five bands, each with a severity description and
   optionally one numeric value. Record which harm category the rating draws
   on: operations, assets, individuals, other organizations, or the wider
   public.
5. Derive the risk rating by looking overall likelihood against impact up in a
   fixed five by five table. Not by averaging, not by re-judging.

For each rating, record which input it draws on, threat-source
characteristics, identified vulnerabilities, or existing safeguards, and record
any uncertainty or subjective judgment used in reaching it.

One register row per risk, fixed columns.

```
Threat  Source  Vulnerability exploited  Likelihood  Impact  Risk
```

Where two risks land on the same score, break the tie on three named factors:
time frame, immediate against future; total cumulative impact if the risk
recurs across the assessment period; and synergy with other listed risks. This
tie-break is for risks. It does not transfer to options on a decision matrix,
where "recurs over the period" means nothing.

Report one aggregate overall risk level for the assessment plus a count of
risks at each level, alongside the per-risk register.

## Root cause, for a single occurrence

Fires when the question asks why something happened, once.

Build an explicit causal chain. Identify the immediate cause, then keep asking
why that cause existed, working backward until you reach a cause with
implications beyond this one occurrence. Do not stop at the first or the most
obvious.

Frame the problem as the unwanted condition or action itself, never as the
system that detected it. "The alert did not fire" is a finding about
monitoring, not the problem.

Never let a bare human-error label or a bare physical condition stand as the
stopping point. Keep asking why until you reach a management, design, or
training explanation.

Select exactly one direct cause, exactly one root cause, and up to three
contributing causes. Describe each specifically to this occurrence rather than
repeating a category label. Naming one root cause is not the single-cause
fallacy: the label is earned only after contributing causes were searched for
and each accepted cause was corroborated.

Require at least two independent pieces of corroborating evidence for each
accepted cause in the chain. Where only one exists, document the alternative
causes you considered and the basis for accepting or rejecting each.

Complete one worksheet per cause: mark it direct, contributing, or root,
describe how it relates to the occurrence, and pair it with its own corrective
action. Every identified cause gets a corrective action, not only the root one.
Word each action so somebody else can verify it independently, and name the
specific cause it addresses.

Pick the technique by the job:

- **Causal factor analysis.** Long chains with several facets.
- **Change analysis.** The cause is obscure. Pick a comparable case that did
  not fail, list every difference between the two regardless of apparent
  relevance, then examine each difference for a role in the failure.
- **Barrier analysis.** A physical or procedural barrier failed. Determine
  whether it worked as designed, whether it was maintained and inspected, why
  the unwanted energy was present, whether it could be evaded, and whether the
  failure was foreseeable. Then check whether identical barriers elsewhere
  share the flaw.
- **Programmatic review.** Recurring or systemic problems. Name the specific
  control that was less than adequate, then name which management element,
  policy, planning, resource allocation, or verification, let that failure
  happen. Do not stop at the control.
- **Human performance evaluation.** Personnel are implicated. Evaluate across
  detection, understanding, action selection, and execution against a
  documented failure-mode list. "Personnel error" on its own is not a finding.

Where a task performed by people is under investigation, reenact it step by
step with the person who performs it while an observer checks against the
written procedure and records discrepancies. Reconstructing it from memory or
documents alone misses the deviation that caused the event.

Where an occurrence recurs, do not open a fresh investigation. Reopen the
original finding, determine why its corrective action failed, and analyze the
new occurrence against the previously fixed case.

## Causal claims about a program

Fires when the question attributes an outcome to a program or an intervention
rather than to one event.

Classify the question first: process, outcome, or net impact. Only a net-impact
question licenses comparing an observed outcome to an estimated counterfactual.
Process and outcome findings describe. They do not attribute cause.

Name the comparison group used, or state its absence explicitly. No comparison
group caps the claim at "associated with". It never reaches "caused by".

License a causal claim only when both conditions are stated: the outcome
changed after the purported cause, and identified external factors were
controlled for. Missing either downgrades the claim to correlational.

Before selecting a design, name at least one external influence the design must
rule out. A design that names none has not engaged the causal question.

Match the design to the program's shape. Full or mandatory coverage with no
untreated population forecloses randomized and matched-comparison designs and
requires a single-group design. Proposing a comparison-group design against a
universally delivered program is a category error to flag, not a design to run.

Where units were randomly assigned, report the pre-exposure equivalence check
between groups. An unverified equivalence check voids the design's claim to
have controlled for confounds. Where the comparison group was not randomly
assigned, name selection bias explicitly and state the adjustment applied, or
flag the claim as unadjusted. Either way, confirm the groups' experiences
stayed separate, with no crossover access and no cross-group communication.
Name contamination as a threat you checked, not one you assumed away.

Where more than one program targets the same outcome, run at least one
falsification check before crediting this one: narrow the outcome measure, or
name an outcome that should not move if this program rather than a co-occurring
one is the cause.

Grade the claim by the design that produced it, and state the tier in the
finding.

```
Randomized controlled experiment
  above  matched quasi-experimental comparison with bias adjustment
  above  single-group time series with statistical controls
  above  before-and-after with no controls, which licenses no causal claim
```

State the limitations as part of the finding, not as an optional caveat: how
conclusive the design is, what trade-offs were made, what remains unaddressed.

## Cost, sensitivity, and value

Fires when money is in the answer.

### Cost sensitivity

Distinct from the weight re-run and from the evidence-sensitivity test.

Pick what to test by computing each cost element's percent share of the total
first, then test the high-share elements as the key drivers. Picking by
intuition tests the elements you find interesting rather than the ones that
move the answer.

Vary exactly one input between its documented minimum and maximum, holding all
others at their point estimate, recompute the total, and repeat. Rank inputs by
how far each moves the total.

Classify a factor **sensitive** if a change of 10 to 50 percent flips the
preferred option's ranking, and **very sensitive** if under 10 percent flips
it.

Never set a bound by a subjective percentage. Trace every tested minimum and
maximum to a documented source: historical data, a vendor quote, or an
elicited expert bound. Where an expert gives a minimum and maximum with no
historical backing, treat those as the 15th and 85th percentile and widen the
tails. Experts capture roughly 70 percent of the true range.

### A cost range rather than a number

Assign each cost element a probability distribution, sum sampled elements over
many iterations, and report the result as a cumulative distribution. State
where the point estimate sits on it as a percentile. Cost distributions are
usually right-skewed and a point estimate commonly lands around the 55th to
65th percentile.

Pick the distribution shape by evidence, not by habit: triangular for a
three-point estimate with nothing else known, lognormal for a right-skewed
relationship with no upper bound, normal only for genuinely symmetric
variation, beta where analogous data show a biased tail, uniform only where
every value in the range is equally likely.

Never model elements that share a common driver as uncorrelated. Assign a
correlation coefficient, 0.3 as a documented default absent better data.
Treating dependent elements as independent understates the true spread.

Set contingency as the cost at the decision-maker's chosen confidence
percentile minus the point estimate. Never as a flat percentage. Allocating
contingency down a work breakdown, allocate proportional to each element's
variance rather than to cost, and make risk-adjusted children sum to the
risk-adjusted parent.

Nothing here runs a simulation. State that one is needed, state what its output
must contain, and say so plainly if it was not run.

### Benefit, cost, and discounting

Normalize costs from different sources or periods to one base year using a
documented inflation index whose scope matches the item.

Base every figure on incremental values only. Exclude sunk costs, exclude
already-realized benefits, exclude pure transfers. Price inputs at the
opportunity cost of the resource, not at its budgeted outlay.

Keep the dollar convention and the discount-rate type consistent throughout: a
real rate with constant dollars, a nominal rate with nominal dollars, never
mixed.

Discount every future benefit and cost, including the nonmonetized ones, to
present value. Produce a year-by-year table of cost, benefit, discount factor
and present value, summed to a total. Where a stream accrues through the year
rather than at year end, use a mid-year factor.

Net present value is total discounted benefits minus total discounted costs. A
negative net present value is a rejection signal. Where benefits across options
are identical, or a policy decision mandates providing the benefit, switch to
cost-effectiveness and report the lowest present-value life-cycle cost for that
benefit level. Where value cannot be fully monetized, still enumerate and
quantify every benefit and cost type and report a supplementary effectiveness
measure rather than dropping into prose.

Report the sensitivity of net present value to the discount rate itself.
Recompute at alternate rates and report the range, not a sentence about which
assumption matters.

Characterize uncertainty by naming its sources and reporting a
probability-weighted expected value or a full distribution. A bare point
estimate presented as certain is the thing this whole block exists to prevent.
Where a worst case is reported alongside the expected value, state the
rationale and the direction of the bias it introduces.

Standing policy rates go stale. A real rate of 7 percent for public investment
and regulatory analysis, Treasury borrowing rates matched to the analysis term
for cost-effectiveness and internal investment work, and a 1.25 multiplier on
public expenditure for the marginal excess burden of taxation, are all defaults
to re-verify against the current published circular before use, not numbers to
quote from here.

Where every option carries a life-cycle cost estimate, select principally by
comparing net present value, with a stated confidence range and a documented
sensitivity analysis of both cost and benefit against the key risks.

## The four challenge techniques

Analysis of competing hypotheses. Team A and Team B. Devil's advocacy. Red
team.

These are not on the escalation ladder and are never triggered by something you
noticed in the question. They run only when the operator names one. When one
runs, the method log records which and who named it, kept apart from the
escalation half of the log.

The reason for the separation is narrow and worth stating. A cost method that
fired because money was in the question, recorded in the same list as a red
team the operator asked for, produces a log that claims the operator requested
something they never mentioned.
