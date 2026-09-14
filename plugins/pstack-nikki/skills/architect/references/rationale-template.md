# Rationale template

The prose that ships alongside the type sketch. One page, sentence-case
headings, no boilerplate. Replace each italic note with content.

## Problem
*What the work is for, and what makes the shape non-obvious. Name the
constraints [Phase A](../SKILL.md#phase-a-ground-the-problem) surfaced: types
to interoperate with, callers you cannot break, invariants crossing in.*

## Usage (caller's view)
*Write this first, before the type sketch. Show the quickstart the consumer
reads plus two or three realistic call sites: what they import, what they call,
what comes back. [Shape](#shape) derives from it, never the reverse.*

## Shape
*The recommended architecture. Data structures first, then how data flows
through the signatures. Name the load-bearing decisions, which invariants the
types encode, where validation lives, and what the system deliberately does not
do. Judge interface depth: what the public surface hides, what stays exposed,
why it is no larger than needed. Cite the principle per decision (say, per
`principle-code-quality`) without restating it.*

## Synthesis decision
*Filled in by [arena](../../arena/SKILL.md). Which candidate became the base
and why, what was adapted from each of the others, what was rejected and why.*

## Tradeoffs accepted
*One bullet per tradeoff: "we accept X in exchange for Y". Name anything a
future reader might mistake for an oversight or for premature optimization.*

## Alternatives considered
*Required. At least one concrete alternative shape, with one line on why it
lost. Judge each on interface depth, not implementation simplicity alone: name
what it exposes to callers and what it hides. Two or three belong here when the
design space had real contenders, one when constraints forced the answer.
Runner candidates belong under Synthesis decision, not here.*

## Open questions and risks
*What the human must weigh in on, and risks worth flagging before
implementation. Phrase them as questions, so the answer resolves them.*

## Next implementation step
*One sentence. The first thing to build against the sketch.*
