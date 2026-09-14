# Cost, sensitivity, and value

Escalation method. Load when money is in the answer. Runs inside step 7
per-option analysis, not beside it. Record that it ran and which trigger fired.

## Cost sensitivity

Pick what to test by computing each cost element's percent share of the total
first, then test high-share elements as key drivers. Picking by intuition tests
elements you find interesting rather than ones that move the answer.

Vary exactly one input between its documented minimum and maximum, holding all
others at point estimate, recompute the total, repeat. Rank inputs by how far
each moves the total.

Classify a factor **sensitive** if a change of 10 to 50 percent flips the
preferred option's ranking, **very sensitive** if under 10 percent flips it.

Never set a bound by subjective percentage. Trace every tested minimum and
maximum to a documented source: historical data, vendor quote, or elicited
expert bound. Expert gives minimum and maximum with no historical backing:
treat those as 15th and 85th percentile and widen the tails. Experts capture
roughly 70 percent of the true range.

## A cost range rather than a number

Assign each cost element a probability distribution, sum sampled elements over
many iterations, report result as cumulative distribution. State where the
point estimate sits on it as a percentile. Cost distributions are usually
right-skewed and a point estimate commonly lands around the 55th to 65th
percentile.

Pick distribution shape by evidence, not habit: triangular for a three-point
estimate with nothing else known, lognormal for a right-skewed relationship
with no upper bound, normal only for genuinely symmetric variation, beta where
analogous data show a biased tail, uniform only where every value in the range
is equally likely.

Never model elements sharing a common driver as uncorrelated. Assign a
correlation coefficient, 0.3 as documented default absent better data. Treating
dependent elements as independent understates the true spread.

Set contingency as cost at the decision-maker's chosen confidence percentile
minus the point estimate. Never as flat percentage. Allocating contingency down
a work breakdown, allocate proportional to each element's variance rather than
to cost, and make risk-adjusted children sum to the risk-adjusted parent.

Nothing here runs a simulation. State that one is needed, state what its output
must contain, say so plainly if it was not run.

## Benefit, cost, and discounting

Normalize costs from different sources or periods to one base year using a
documented inflation index whose scope matches the item.

Base every figure on incremental values only. Exclude sunk costs, exclude
already-realized benefits, exclude pure transfers. Price inputs at the
opportunity cost of the resource, not at its budgeted outlay.

Keep dollar convention and discount-rate type consistent throughout: real rate
with constant dollars, nominal rate with nominal dollars, never mixed.

Discount every future benefit and cost, nonmonetized ones included, to present
value. Produce a year-by-year table of cost, benefit, discount factor and
present value, summed to a total. Stream accrues through the year rather than
at year end: use a mid-year factor.

Net present value is total discounted benefits minus total discounted costs. A
negative net present value is a rejection signal. Benefits across options
identical, or a policy decision mandates providing the benefit: switch to
cost-effectiveness and report the lowest present-value life-cycle cost for that
benefit level. Value cannot be fully monetized: still enumerate and quantify
every benefit and cost type and report a supplementary effectiveness measure
rather than dropping into prose.

Report sensitivity of net present value to the discount rate itself. Recompute
at alternate rates and report the range, not a sentence about which assumption
matters.

Characterize uncertainty by naming its sources and reporting a
probability-weighted expected value or a full distribution. A bare point
estimate presented as certain is the thing this whole block exists to prevent.
Worst case reported alongside expected value: state the rationale and the
direction of the bias it introduces.

Standing policy rates go stale. A real rate of 7 percent for public investment
and regulatory analysis, Treasury borrowing rates matched to the analysis term
for cost-effectiveness and internal investment work, and a 1.25 multiplier on
public expenditure for the marginal excess burden of taxation, are all defaults
to re-verify against the current published circular before use, not numbers to
quote from here.

Every option carries a life-cycle cost estimate: select principally by
comparing net present value, with a stated confidence range and a documented
sensitivity analysis of both cost and benefit against the key risks.
