# Collisions: five tie-breaks

Load when two rules in this skill appear to conflict, or when the report uses
a named paper format, whoever chose it. One ruling each.

- Data plural. Strunk rules "data" plural; Daniel routes around the fight.
  Adopt Daniel's dodge ("statistics are," "information is"). Agent has no
  standing in a usage war, no way to know the reader's preference.
- Hedging versus calibration. Empty hedging banned, calibrated probability
  mandatory. Ship as one rule: "it would appear costs may rise" is the banned
  half, "costs are likely (55 to 80 percent) to rise" is the required half.
  Marked as a synthesis, like the container law.
- Conclusion first versus hostile audience. Daniel wins: the conclusion goes
  in the first paragraph. The indirect approach that softens the blow for a
  hostile reader is a deviation the operator may invoke, never a default the
  agent chooses.
- Analysis order versus presentation order. Analyze options before comparing
  them, generate at least two before choosing -> order of thinking. Conclusion
  in the first paragraph -> order of writing. Not a conflict. Do the work in
  the analytic order, present it in the reader's order.
- Named format versus exclusion list. Background paper is background by
  construction; a staff study's Part 1 states the problem and its Part 2
  defines terms. Where the report uses a named format, whoever chose it, the
  format wins for exactly the elements its skeleton requires, and the exclusion
  list governs everything else. Name in one line, in the format-elements note
  (an admissible end-matter item, check 2), every excluded element the format
  claimed, by their names on the exclusion list, not by the format's part
  names. Every one the skeleton claimed, not the ones you noticed first; a
  subset fails check 5. The conclusion still leads: put it in the first
  paragraph whatever number the skeleton gives it. This is a tie-break, so it
  needs no deviation record.

## Excluded elements each format claims

| format | excluded elements claimed |
|---|---|
| point, talking, position paper | none |
| background paper, bullet background paper | summarize background |
| staff study | restate the problem; define terms; summarize background; explain calculations |
| running estimate | restate the problem; summarize background; explain calculations |

Design mark: skill-authored, not source-quoted. `scripts/check-report.sh`
reads this table for check 5. Each row's derivation, so an auditor can check
it without redoing it:

- Point, talking, position paper claim nothing: none of the three has a
  skeleton in references/skeletons.md, and none of their descriptions in
  references/structure.md (point paper, talking, and position paper) name an
  excluded element.
- Background paper, bullet background paper claim "summarize background":
  both job descriptions in references/structure.md say so directly — bullet
  background paper's job is to "summarize an attached package," background
  paper's job is to "condense a complex issue... for the reasoning" — and
  both are background by construction, per the ruling above; neither has a
  references/skeletons.md skeleton.
- Staff study claims four: references/skeletons.md:19 (Part 1, "the
  statement of the problem" -> restate the problem), :24-26 (Part 2,
  "assumptions, criteria and definitions" -> define terms), :35-37 (Part 3,
  "some background information is necessary" -> summarize background),
  :41-46 (Part 3, "show how you tested," "show how you weighed" -> explain
  calculations). Confirmed at four by case 8.
- Running estimate claims three: references/skeletons.md:121 (section 2,
  "the restated mission" -> restate the problem), :97-120 (section 1,
  "situation and considerations" -> summarize background), :130-137
  (sections 4-5, "analyze," "use a decision matrix" -> explain calculations).
