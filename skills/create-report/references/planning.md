# Planning: steps 1 to 5

Load when working steps 1 to 5: assignment, audience, notes, thesis, plan.
Recommendation machinery: references/recommendation.md.

Content owned elsewhere, linked never copied:

- Paragraph template, cover letter, paper formats: `references/structure.md`.
- Sentence layer, numbers, likelihood ladder, weasel list:
  `references/style.md`.
- Opinion adjudication, evidence tests, graphs, footnotes, citation template:
  `references/evidence.md`.
- Checks, key-assumptions-check procedure, structured challenge techniques:
  `references/checklist.md`.

---

## Step 1: Assignment

Write out the specific question the report answers before anything else. Topic
is the question; thesis is the answer. Most common failure: agent answers a
question no one asked.

- Bad: the instruction was "look into the Schlerg acquisition," so the report
  surveys the company. "Look into X" is not an assignment, and a survey is not
  an answer.
- Good: the question is written first, "Should we acquire the Schlerg
  Company?", and every sentence in the report serves that one question.

Assignment asks yes or no -> answer yes or no.

- Bad: asked "Should we open a second plant?", the report lays out
  considerations and leaves the reader to decide.
- Good: asked "Should we open a second plant?", the report opens with "No,"
  then gives the reasons.

One controlling purpose governs the whole report, and every sentence serves
it. A sentence serving no purpose is not neutral; it is a leak. Cannot say
which purpose a sentence serves -> cut it.

### Get the problem statement approved

Question came from someone else -> get the problem statement approved before
working on it. Enforcement step, not courtesy: you and the decision-maker
agree on the problem before effort is spent.

Cast the problem statement as who, what, when, why, and how, then state it in
one of three forms (from Tongue and Quill, TQ-17 / `998664c6e1ca`):

1. As a question: "What should we do to ...?"
2. As a statement of need or purpose: "The base needs to be able to detect
   ..."
3. As an infinitive phrase: "To detect and end the causes of ground mishaps
   ..."

Narrow it. TQ-17 (`998664c6e1ca`): "Vague or fuzzy problem statements lead to
unacceptable reports." Its worked example: for drug use among junior Airmen,
"To reduce the crime rate on base" is too broad; "To detect and end the causes
of amphetamine and barbiturate use among the junior Airmen at
Wright-Patterson AFB" is the usable statement.

Solve the root cause, not the symptom. FM 5-0 (FM-s2 / `e597a36d8409`): "A
problem exists when the current state or condition differs from or impedes
achieving the desired end state." Its procedure: compare the current situation
to the desired end state, define the boundaries, answer who, what, when,
where, and why the problem affects and occurred, and only then write the draft
statement. Problem came from a higher authority -> "it is best to submit the
problem statement to the decision maker for approval."

- Bad: the assignment asks what to do about falling morale, and the report
  explains how morale fell. Answering "how it happened" when asked "what to do
  about it" is the classic miss.
- Good: the report names the root cause, then answers what to do about it.

### The first key assumptions check

Run the key assumptions check here, at the start, against the answer the
assignment already presumes. Every assignment smuggles in assumptions; name
them before they harden. Runs twice, here and at step 8. Procedure and the
questions to ask: `references/checklist.md`. Record its output as a planning
artifact.

---

## Step 2: Audience

Set two dials together, before drafting. Daniel states them as a matched pair:
omit as much as possible, and be as technical as possible. First dial is what
the reader already knows; second is what the reader can absorb. Turn them
together, because each bounds the other.

- Bad: the report defines "amortization" for a reader who is the company's
  own CFO. Explaining what the reader knows insults the reader.
- Good: the report assumes the CFO knows amortization and spends its words on
  the judgment the CFO does not yet have.

Default reader, unless the assignment says otherwise: intelligent, suspicious,
busy. Intelligent -> do not over-explain. Suspicious -> every claim needs its
support. Busy -> answer comes first, nothing is padding.

### Four roles, not one reader

One report usually has four audiences at once. Address all four, not the one
you happen to be writing to. From Tongue and Quill (TQ-3 / `9263c6f6f634`):

- Primary receiver: "The person you directly communicate with either verbally
  or in writing."
- Secondary receiver: "People you indirectly communicate with through the
  primary receivers." The wing commander e-mails the first sergeants (primary);
  the troops the sergeants forward it to are the secondary receivers.
- Key decision makers: "the most powerful members of the audience ... the ones
  that really make the decisions." Knowing who they are focuses the delivery.
- Gatekeepers: "people in the chain that typically review the communication
  before it reaches your intended audience." Knowing their expectations "can
  save you embarrassment."

Sentence-level tone, jargon density, and the choice of paper format follow
from the audience. Formats: `references/structure.md`.

---

## Step 3: Notes

Collect the facts the report will use as a distinct artifact, separate from
both the source material and the draft. Counter to context bleed: for an
agent, the notes step is what stops session context or source text from being
pasted straight into the report.

Two rules make notes notes and not a transcript:

- Transform each idea into your own words. Understand the author's point,
  restate it. Do not copy the text.
- Record each fact with its source, so every note can be traced later.

Source reliability and citation mechanics live in `references/evidence.md`.
This step only requires that the source is captured with the fact.

---

## Step 4: Thesis

Form the thesis from the notes, after them, never as a starting assumption.
Thesis is the answer the work produced. An agent that fixes the thesis first
and then gathers support has inverted the process and will cherry-pick.

- Bad: "The Schlerg Company is a strong acquisition target" is decided first,
  and the notes are mined for anything that agrees.
- Good: the notes are reviewed, and the thesis is whatever they actually
  support, "The Schlerg Company is not a suitable acquisition target,"
  including when that is the opposite of the expected answer.

State the thesis with its primary supporting reasons grouped into major
categories, not as a flat list of every point.

- Bad: the thesis trails nine individual problems in a run.
- Good: the thesis groups them into three categories, poor finances, poor
  labor relations, and poor public relations, so the reader can hold the shape
  of the argument.

This grouped thesis is what the first paragraph will carry. How that paragraph
is built: `references/structure.md`.

---

## Step 5: Plan

Build the plan in two passes, and write no prose until both are done.

1. Skeleton plan: the order of the arguments, top to bottom. This is the order
   the first paragraph will announce and the body will follow.
2. Final plan: correlate every note to the point it supports.

Final plan is where exclusion happens. A note supporting no point on the
skeleton gets cut here, before drafting, never discovered in the draft. This
is what makes the draft "largely automated": plan honest -> drafting step has
nothing left to decide.

- Bad: all the notes are carried into the draft, and the irrelevant ones are
  trimmed later, or worse, left in because they were already written up.
- Good: each note is placed under a point or cut, so the draft is written from
  a plan where every remaining note has a job.

Any point that is divided must divide into at least two parts. A section with a
single sub-point means the division was wrong; fold it back up.

Where the report recommends, this step lays out the criteria and the decision
matrix the analysis already used; both are standards, not work to do here. The
send-back and the four forms that meet the standard are in SKILL.md step 5.
`references/recommendation.md` specifies those standards.
