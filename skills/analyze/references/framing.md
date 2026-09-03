# Framing and sizing

Steps 1 to 3. Load first.

Environment first as its own product, then the problem.

## Step 1: the environment

Write what bears on the decision across five kinds of condition. Not all five
apply to every question; name the ones that do, say the rest are empty.

- Physical: place, hardware, capacity, distance, anything with a location.
- Social: people affected, their relationships, what they will tolerate.
- Political: who holds authority, what is already committed, whose approval
  the course needs.
- Informational: what is known, what is not, who controls the flow.
- Infrastructural: systems and services the course would run on or break.

Name which other parties' actions could degrade or block the course, not only
which conditions favour it. Frame listing only tailwinds is not written yet.

## The actors

Table, one row per actor relevant to the decision.

```
Actor              What it wants            Where that conflicts
Support team       Predictable hours        Coverage window the plan needs
Finance            Flat headcount cost      Any option that adds staff
```

Conflicts go both directions: actor against actor, and actor against the
deciding organization's own goals. Actor with no conflict recorded is either
irrelevant or under-examined; decide which and say so.

## Step 2: the problem

Three named parts. All three, in this order.

1. The tension between current conditions and desired conditions.
2. Which elements of the environment must change to close it.
3. The limitations that bound the response.

Problem stated as a solution ("we need to migrate to X") is not a problem
statement. Rewrite it as the tension it stood in for.

Then cast the same question a second way, as who, what, when, why, and how.
Two shapes catch different omissions: three-part version exposes a missing
desired end state, five-question version exposes a missing deadline or missing
owner. Write both.

Question came from someone else: get the problem statement approved before
working on it, record who approved it. Approval not sought: record that
instead. Unrecorded approval field reads as approved, which is the wrong
default.

### Terms

Define terms the analysis leans on, short list. Term used with a narrower
meaning than a reader would assume, or term with contested meaning inside the
organization, goes here. Not a glossary of the obvious.

### The constraints list

Itemized, never a paragraph. Legal, resource, geographic, schedule, and other
operational limits, one per line. Every option gets checked against this list
directly, so a constraint buried in prose is a constraint nobody will apply.

```
C1  Cannot exceed the approved FY26 infra line, $340k
C2  Must retain data in-region under the DPA
C3  No change during the November freeze
```

### Classify the problem's structure

Pick one, write down which and why. Class sets what the rest of the run has to
produce.

- **Well structured.** Nearly all needed information in hand, known methods
  apply, one verifiable answer exists. Often gets an answer, not an option
  comparison.
- **Medium structured.** Default bucket. Some information missing, method
  mostly clear, more than one defensible answer.
- **Ill structured.** People disagree on what the true problem is, on the
  desired end state, or on whether that end state is reachable. Expect a
  package of measures rather than a single lever. That package is still one
  course; see the close-call and package rulings in references/comparison.md.

## Step 3: size the work and route the methods

Scale the analysis to the problem, not to the format. Three things decide how
much work a question earns: complexity, your experience with this kind of
problem, time available. Simple problem gets a decision, not a full option
comparison.

### The depth tiers

Design decision, not a sourced rule. No source says how many techniques a
question earns.

**Cheap tier, always.** Frame, evidence, criteria, options, per-option
analysis, matrix, both key-assumptions-check runs, sensitivity test. Every
question gets this, including ones that end up needing nothing else.

**Escalation, on a trigger.** A named method runs only when something in the
question calls for it.

| Trigger in the question | Escalate to |
|---|---|
| Money in the answer, cost or value | Cost, sensitivity, benefit-cost |
| A cause claim, why did this happen | Root cause or causal-design tiers |
| A stated likelihood in the answer | Probability derivation |
| A risk register asked for | Risk rating and register |

One file each: references/method-cost.md, references/method-root-cause.md or
references/method-causal-claims.md, references/evidence.md for probability,
references/method-risk.md. Load only the one that fired. Record which trigger
fired for each you run, in the method log's escalation half.

**Stop** when the next method would change neither the recommendation nor its
confidence.

**The four challenge techniques are not on this ladder.** Analysis of
competing hypotheses, Team A and Team B, devil's advocacy, and red team run
only when the operator names one. Never trigger one because the question looked
contested. One runs -> method log's other half, recorded with who named it.
Confuse the two halves and an auto-routed cost method ends up labelled as
something the operator asked for. See references/challenge-techniques.md.

### Picking a technique

Name the specific task before reaching for anything, then take the technique
that does that task. Three jobs, not interchangeable.

- **Diagnostic** techniques make arguments, assumptions and gaps visible.
- **Contrarian** techniques attack the current line head on.
- **Imaginative** techniques produce new insight, other perspectives, other
  outcomes.

Weigh cost before running. Brainstorming and devil's advocacy cheap to
understand and run. Rest demand more skill, more time, more commitment.

Routed to causation: pick the technique by the job. Table and procedures in
references/method-root-cause.md.

## Hands forward

Sections 1, 10. Section 10 opens here at step 3, written as you go, not
reconstructed at the end.
