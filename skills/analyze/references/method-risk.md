# Risk rating and register

Escalation method. Load when question asks for risk register or rating. Runs
inside step 7 per-option analysis, not beside it. Record that it ran and which
trigger fired.

Declare two things before rating anything, so scale is fixed up front rather
than improvised per risk:

- Approach: quantitative, qualitative, or semi-quantitative.
- Orientation: threat-oriented, asset-oriented, or vulnerability-oriented.

Then rate on five-band scale, Very Low to Very High, each band anchored to a
numeric range.

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

Per rating, record which input it draws on: threat-source characteristics,
identified vulnerabilities, or existing safeguards. Record any uncertainty or
subjective judgment used reaching it.

One register row per risk, fixed columns.

```
Threat  Source  Vulnerability exploited  Likelihood  Impact  Risk
```

Two risks land on same score, break tie on three named factors: time frame,
immediate against future; total cumulative impact if risk recurs across
assessment period; synergy with other listed risks. Tie-break is for risks
only. Does not transfer to options on a decision matrix, where "recurs over the
period" means nothing.

Report one aggregate overall risk level for assessment, plus count of risks at
each level, alongside per-risk register.
