# Framing and sizing

Steps 1 to 3. Load before anything else. Everything downstream checks against
the constraints list these steps produce, so a vague frame quietly weakens
every later verdict.

The environment and the problem are two separate products in a fixed order.
Write the environment first, as its own thing, and let it feed the problem
statement. Folding it in as a preamble collapses the two, and the constraints
stop being checkable.

## Step 1: the environment

Write what bears on the decision across five kinds of condition. Not all five
apply to every question; name the ones that do and say the rest are empty.

- Physical: place, hardware, capacity, distance, anything with a location.
- Social: the people affected, their relationships, what they will tolerate.
- Political: who holds authority, what is already committed, whose approval
  the course needs.
- Informational: what is known, what is not, who controls the flow.
- Infrastructural: the systems and services the course would run on or break.

Name which other parties' actions could degrade or block the course, not only
which conditions favour it. A frame that lists only tailwinds has not been
written yet.

## The actors

A table, one row per actor relevant to the decision.

```
Actor              What it wants            Where that conflicts
Support team       Predictable hours        Coverage window the plan needs
Finance            Flat headcount cost      Any option that adds staff
```

Conflicts go in both directions: between actors, and between an actor and the
deciding organization's own goals. An actor with no conflict recorded is either
irrelevant or under-examined; decide which and say so.

## Step 2: the problem

Three named parts. All three, in this order.

1. The tension between current conditions and desired conditions.
2. Which elements of the environment must change to close it.
3. The limitations that bound the response.

A problem stated as a solution ("we need to migrate to X") is not a problem
statement. Rewrite it as the tension it was standing in for.

Then cast the same question a second way, as who, what, when, why, and how.
The two shapes catch different omissions: the three-part version exposes a
missing desired end state, the five-question version exposes a missing
deadline or a missing owner. Write both.

Where the question came from someone else, get the problem statement approved
before working on it, and record who approved it. Where approval was not
sought, record that instead. An unrecorded approval field reads as approved,
which is the wrong default.

### Terms

Define the terms the analysis leans on, as a short list. A term used with a
narrower meaning than a reader would assume, or a term with a contested
meaning inside the organization, goes here. This is not a glossary of the
obvious.

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

Pick one, and write down which and why. The class sets what the rest of the
run has to produce.

- **Well structured.** Nearly all the needed information is in hand, known
  methods apply, and one verifiable answer exists. Often gets an answer, not
  an option comparison.
- **Medium structured.** The default bucket. Some information missing, method
  mostly clear, more than one defensible answer.
- **Ill structured.** People disagree on what the true problem is, on the
  desired end state, or on whether that end state is reachable. Expect the
  answer to be a package of measures rather than a single lever. That package
  is still one course; see the close-call and package rulings in
  comparison.md.

## Step 3: size the work and route the methods

Scale the analysis to the problem, not to the format. Three things decide how
much work the question earns: how complex it is, how much experience you have
with this kind of problem, and how much time there is. A simple problem gets a
decision, not a full option comparison.

### The depth tiers

This is a design decision, not a sourced rule. No source says how many
techniques a question earns.

**Cheap tier, always.** Frame, evidence, criteria, options, per-option
analysis, matrix, both key-assumptions-check runs, sensitivity test. Every
question gets this, including the ones that end up needing nothing else.

**Escalation, on a trigger.** A named method runs only when something in the
question calls for it.

| Trigger in the question | Escalate to |
|---|---|
| Money in the answer, cost or value | Cost, sensitivity, benefit-cost |
| A cause claim, why did this happen | Root cause or causal-design tiers |
| A stated likelihood in the answer | Probability derivation |
| A risk register asked for | Risk rating and register |

All four live in methods.md. Record which trigger fired for each one you run,
in the method log's escalation half.

**Stop** when the next method would change neither the recommendation nor its
confidence.

**The four challenge techniques are not on this ladder.** Analysis of
competing hypotheses, Team A and Team B, devil's advocacy, and red team run
only when the operator names one. Never trigger one because the question
looked contested. When one does run, it goes in the method log's other half,
recorded with who named it. Confusing the two halves is how an auto-routed
cost method ends up labelled as something the operator asked for.

### Picking a technique

Name the specific task before reaching for anything, then take the technique
that does that task. Three jobs, and they are not interchangeable.

- **Diagnostic** techniques make arguments, assumptions and gaps visible.
- **Contrarian** techniques attack the current line head on.
- **Imaginative** techniques produce new insight, other perspectives, other
  outcomes.

Weigh the cost before running. Brainstorming and devil's advocacy are cheap to
understand and run. The rest demand more skill, more time, and more commitment.

Never present a technique's output as proof the judgment is right. Running
these raises what the assessment is worth to its reader. It does not raise its
accuracy.

### Route a causal question by the job

If step 3 routed to causation, pick the technique by what it does.

- Causal factor analysis: long chains with several facets.
- Change analysis: the cause is obscure.
- Barrier analysis: equipment or a barrier failed.
- Programmatic review: recurring or systemic problems.
- Human performance evaluation: personnel are implicated.

Procedures in methods.md.

## What steps 1 to 3 hand forward

Handover section 1, the problem frame: the environment by condition type, the
actor table, the three-part problem statement, the same question in who, what,
when, why and how, the approval record, the terms defined, the itemized
constraints list, the structure class, and the depth tier with the triggers
that fired.

Handover section 10 opens here: which methods you chose and which trigger
fired for each, so the log is written as you go rather than reconstructed at
the end.
