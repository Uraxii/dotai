# Sample reports: one bad, one good

Worked example of the report contract. Two versions of the same internal
recommendation, written from the same facts. First breaks the contract on
purpose. Second obeys it. After each, a list ties specific lines to the rule
they break or satisfy. The pair is original writing, not reproduced from any
source.

Report shapes referenced below: references/structure.md. Likelihood ladder and
weasel list: references/style.md. Numbered checks:
references/checklist.md.

## The facts both versions use

Scaffolding for this example, not part of either report. Both report bodies
below are written as business prose, the register this skill produces, not the
register this file's own commentary uses. RadixParts ships about 8,000
regional parcels a month. Its carrier contract is expiring and one carrier
must be chosen for the coming year. Three candidates, from the same data both
versions draw on:

- Meridian Freight: $7.20 per parcel, 94 percent on time, 2.1 days transit.
- Coastal Parcel: $6.40 per parcel, 89 percent on time, 2.8 days transit.
- Union Dispatch (the incumbent): $7.90 per parcel, 96 percent on time, 1.9
  days transit.

Prices come from the carriers' rate cards. On-time and transit figures come
from an independent scorecard. Incumbent figures also come from RadixParts's
own shipping logs.

## The bad report, as written

**Regional Carrier Costs**

You asked me in Tuesday's standup to look into our shipping situation, so I
completed a review of all three carriers and here is what I found. As I said in
Slack this morning, our regional contract is expiring and we need to pick
someone. Just to restate the problem: we ship a lot of parcels every month and
the contract is up, so the question is what to do about carriers. On-time rate,
which means the percent of parcels delivered by their promised date, is one of
the things I looked at, along with cost and transit time.

**Background**

We currently use Union Dispatch. Our volume is 8,000 parcels a month. The three
carriers I researched were Union Dispatch, Meridian Freight, and Coastal
Parcel. I got most of this from the carriers' own websites and a report someone
in ops shared with me.

**The Carriers**

Meridian is $7.20. Coastal is $6.40. Union is $7.90. The on-time rates are 94
percent, 89 percent, and 96 percent. Transit times are 2.1 days, 2.8 days, and
1.9 days. Coastal is significantly cheaper and their prices are lower then ours.
Meridian appears to be a solid choice, and there is a serious possibility that
Coastal's service may well improve over time. Union is doubtless the safest.
Reportedly Meridian handles peak season fine.

**Costs**

To get the annual figure I took the $0.70 difference, multiplied it by 8,000,
and then multiplied by 12, which gives $67,200. See Figure 1: Costs. This is a
substantial number and will effect our budget. Meridian will keep its 94
percent on-time rate. I am highly confident it is very likely to work out.

**Other Factors**

There are good arguments for all three, so it is really up to you which one to
go with. Meridian is the best value.[1]

[1] This is my conclusion based on the analysis above.

P.S. I forgot to mention above, Coastal also has a fuel surcharge that changes
the cost picture, but I will leave that note here at the end.

## What the bad report breaks

Failure modes, the skill's four named ones:

- Context bleed: "in Tuesday's standup," "As I said in Slack this morning."
  Session talk pasted in, not transformed notes.
- Agent narration: "I completed a review," "Just to restate the problem," the
  step-by-step multiplication, the footnote on its own conclusion.
- Revision as append: "P.S." bolts a cost fact onto the end, outside an order
  the opening never promised.
- False confidence: "Meridian will keep its 94 percent on-time rate" states an
  inference as a fact; "highly confident it is very likely" gives a conclusion
  with no calibrated likelihood.

Checklist coverage. Each check catches at least the line named here.

| Check | Where the bad report trips it |
|---|---|
| 1 | First paragraph restates the problem; no grouped reasons |
| 2 | No order announced, so the body follows none |
| 3 | Subheads name topics, state no sub-conclusion |
| 4 | Conclusion sits in the last line, not the first paragraph |
| 5 | Restated problem, research announcement, background summary, term |
|   | definition, explained calculation, self-footnote, and an inference |
|   | stated in the form of a fact, all present |
| 6 | "$7.20. Coastal is $6.40. Union is $7.90" listed, not compared |
| 7 | "significantly," "appears," "substantial" |
| 8 | "Figure 1: Costs" titled by topic, no thesis |
| 9 | Sources are "websites" and "a report someone shared"; one kind |
| 10 | Rival claims never weighed against each other |
| 11 | Title "Regional Carrier Costs" states a topic, not a conclusion |
| 12 | "lower then ours," "will effect our budget," spell-checker blind |
|   | spots the read-aloud pass would have caught |
| 13 | "highly confident it is very likely" pairs confidence with |
|   | likelihood in one sentence, and uses no published ladder |
| 14 | "serious possibility," "may well," "doubtless," "reportedly" |
| 15 | "Our volume is 8,000 parcels a month" stated as bare fact |
| 16 | No criteria, no weights, no decision matrix |
| 17 | "it is really up to you" hands the decision back |
| 18 | Volume stated with no assumptions check behind it; the whole cost |
|    | case rests on the $0.70 gap and nothing says what breaks if the |
|    | fuel surcharge closes it |
| 19 | Typos and the append show no three-pass edit ran |
| 20 | Coastal's weakness and the losing options are never faced |
| 21 | "Meridian will keep its 94 percent on-time rate" and "Meridian is |
|    | the best value" name nothing that would change either |
| 22 | "in Tuesday's standup" and "As I said in Slack this morning" paste |
|    | session context; "websites and a report someone in ops shared with |
|    | me" is the whole sourcing, with no notes file behind any figure |
| 23 | The report misses most of the checks above and records not one of |
|    | them as an authorised deviation |

Checks 18, 19 and 23 are process checks, not lines of report text. Bad report
fails them by evidence: unmarked volume figure shows no assumptions check
informed it, no "if X is wrong, Y breaks" line shows the sensitivity test ran,
blind-spot typos plus the append show the edit passes never ran, absent
deviations block shows nothing was authorised. Check 22 is half text check,
half process check: pasted session talk is on the page, missing notes file is
not.

## The good report, as written

**Standardize regional shipping on Meridian Freight for the coming year**

Sign Meridian Freight for the coming contract year. Meridian wins on the
balance of the three criteria fixed before the carriers were compared: it costs
less than the incumbent, it holds the second-best on-time rate of the three,
and its transit time trails the incumbent by a fraction of a day. This report
takes those three in order, cost, on-time reliability, then the volume
assumption that could change the ranking, and closes with the recommendation
and the single condition that would reverse it.

**Meridian cuts cost without gutting service**

Meridian bills $7.20 per parcel against the incumbent Union Dispatch's $7.90, a
saving of $0.70 per parcel, or about 9 percent. At the current 8,000 parcels a
month that is roughly $5,600 a month and near $67,000 over the contract year.
Coastal Parcel is cheaper still at $6.40, $0.80 under Meridian, but it buys that
gap with the weakest reliability of the three, below.

**Meridian's on-time rate is second, and close enough**

Meridian delivers on time 94 percent of the time, two points under Union
Dispatch's 96 percent and five points over Coastal's 89 percent. Coastal's
transit averages 2.8 days against Meridian's 2.1 and Union's 1.9, so Coastal's
lower price comes with both the slowest and the least reliable service.
Meridian is likely (55 to 80 percent) to hold its 94 percent rate at the
current volume; the rate has stayed between 93 and 95 percent across the two
quarters on record. The ladder this figure sits on is published in
references/style.md. Confidence in the judgment is moderate, since it rests on
two quarters of an independent scorecard rather than a full year.

**Weighing the three against the criteria**

The criteria were weighted before scoring: landed cost 0.40, because cutting
cost is this year's stated goal; on-time rate 0.35, because all three clear the
88 percent service floor; transit time 0.25, the least differentiating factor.
Each carrier scored 0 to 10 per criterion, higher better. The scores are
judgment, not measurement, and the cost column is where that judgment matters
most.

| Criterion (weight) | Meridian | Coastal | Union |
|---|---|---|---|
| Landed cost (0.40) | 7 | 10 | 4 |
| On-time rate (0.35) | 8 | 4 | 10 |
| Transit time (0.25) | 9 | 5 | 10 |
| Unweighted total | 24 | 19 | 24 |
| Weighted total | 7.85 | 6.65 | 7.60 |

Meridian and Union tie unweighted at 24; weighting toward cost, this year's
priority, gives Meridian the edge at 7.85 against Union's 7.60. Coastal trails
at 6.65, because its price advantage cannot cover a five-point reliability gap.

**The volume assumption is what could flip the ranking**

Assumption: regional volume stays near 8,000 parcels a month through the
contract year. If it climbs above 10,000, Meridian's tier-two rate of about
$6.60 undercuts Coastal and widens Meridian's lead. If it falls below 5,000, no
volume discount applies to any carrier and the ranking narrows to on-time rate,
where Union Dispatch leads. Across the volume band actually forecast, the
recommendation holds.

**Recommendation**

Sign Meridian Freight for the coming contract year. The decision before you is
to approve or decline that signing. One condition would reverse it: if
Meridian's monthly on-time rate falls below 92 percent for two consecutive
months, reopen the comparison, because below that point its reliability edge
over Coastal no longer justifies the $0.80 price gap.

Sources: Meridian Freight and Coastal Parcel rate schedules, both effective
2026-07-01; on-time and transit figures from the ParcelIndex regional carrier
scorecard, second quarter 2026; incumbent cost and service figures from
RadixParts shipping logs, January to June 2026. Prices come from the carriers'
rate cards; the on-time figures come from the independent scorecard, not any
carrier's own marketing.

## What the good report satisfies

| Check | Where the good report satisfies it |
|---|---|
| 1, 2 | First paragraph carries the conclusion plus reasons in three |
|   | categories, cost, reliability, and one risk, and announces the |
|   | order the body follows |
| 3, 4 | The title states the conclusion; every subhead states a |
|   | sub-conclusion that carries the argument read alone |
| 6 | Every number compared: $7.20 against $7.90, $6.40 against $7.20, 94 |
|   | against 96 against 89 |
| 7 | No vague evaluative terms stand in for the comparison |
| 9 | Sources precise, dated, and varied in kind, with the note on why the |
|   | on-time figures come from the scorecard and not carrier marketing |
| 13, 14 | "likely (55 to 80 percent)" with confidence in its own |
|   | sentence, and no weasels |
| 15 | The volume assumption is marked, and its consequence stated in both |
|   | directions |
| 16 | Criteria, the weights with their rationale, and both totals |
|   | summarized in the body |
| 17 | Commits to one course; the reader approves or declines |
| 18 | The visible assumption is the assumptions check's residue |
| 19 | The clean prose is the edit passes' residue |
| 21 | The 92 percent falsifier |
