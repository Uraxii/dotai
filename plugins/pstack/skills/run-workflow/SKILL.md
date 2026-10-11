---
name: run-workflow
description: "Run a saved workflow or design an auditable workflow for a large migration, a multi-part change, or work a human reviews later. Use for /run-workflow, 'run workflow', a large migration, or when no narrower playbook applies."
disable-model-invocation: true
---

# Run workflow

Select a saved workflow before you design a custom workflow. The workflow defines phases, required checks, and a decision trail.
For authorized production code changes, read and use the saved [Code-change workflow](workflows/code-change-workflow.md).
Use that workflow for each production-code unit in a broader custom run.
If no saved workflow fits a non-code task, design one with the phases below.
Read-only investigations, proposals, plan runs, and throwaway prototypes keep their requested scope and stop point.
If a prototype becomes authorized production work, start the saved code-change workflow before its production writer.

## Start

Find or create the run bead per [Run records](../ticket-work/references/run-records.md), and create the phase beads per its Phases of a skill section. The first phase bead reads the Principles section of the **poteto-mode** skill. Then create one phase bead for each phase below.

## Phase A: Frame

Ground first, then commit. Don't start the run until you can state:

- The definition of done as a falsifiable predicate (the **prove-it-works** principle skill).
- Scope, quantified: rough units and effort, plus the blockers grounding surfaced.
- The rigor level, biased high. One-way doors and high blast radius get more. Reversible low-stakes steps get less. Rigor is gates and artifacts, not "try harder".

Present the framing and tradeoffs before committing to a long run. Reversible work proceeds (the **never-block-on-the-human** principle skill), but a multi-hour run earns one checkpoint.

## Phase B: Design the workflow

Read the selected saved workflow before execution. For production code, [Requirements planning](workflows/code-change-workflow.md#requirements-planning) defines the mode decision.
If no saved workflow fits, define the custom steps below.

Decompose into atomic, independently-landable units. Sequence riskiest-unknown-first. Scaffold and verification come before features (the **foundational-thinking** principle skill).

- Build the verification harness before the work, with the baseline captured from the pre-change state, so the check reads as "old value vs new value".
- For production code, follow the recorded mode in [Requirements planning](workflows/code-change-workflow.md#requirements-planning). For non-code design decisions that are difficult to reverse, request **architect** Phases A through C for a design-only handoff. The caller owns implementation. A second arena over a settled design is over-engineering (the **laziness-protocol** principle skill).
- Decide what fans out. Parallelize only across seams, and give each worker its own worktree or branch (the **separate-before-serializing-shared-state** principle skill). Don't over-fan.
- Write the designed phase list down. That list is what the human reviews.

Return the workflow before execution when the caller brief requests that handoff. Otherwise, execute the design.

Create each of its steps as a child bead of the Phase C phase bead. Run each under the Phase C loop discipline, and weave the Phase D log through them, a row as each step lands, rather than saving the whole trail for the end.

## Phase C: Run the loop

Each unit is an experiment. State the hypothesis, make the smallest change, measure against the predicate on the real artifact, keep it if it advanced, revert it if it didn't.
Apply the **sequence-verifiable-units** principle skill, verifying each unit before starting the next instead of batching checks at the end.

- Verify by inspecting the artifact, never a self-report. When something passes too easily, suspect the observation method before the system.
- Pair delegated work with a judge. If a worker games the gate, reset and harden the contract. If the gate itself is wrong, fix the gate in its own change rather than routing around it.
- A verdict is VERIFIED, NOT VERIFIED, or INCONCLUSIVE. Inconclusive is not a pass. Don't hide a negative.

## Phase D: Keep the audit trail

Log the run via the **show-me-your-work** skill. run-workflow's work is usually ambitious enough to commit the trail so the reviewer can read it in the PR. The trail plus the diff is what lets the human come back and trust the work.

## Phase E: Verify and hand back

Check the whole against the Phase A predicate on the real product, not just the harness. Encode any recurring correction as a gate, a lint rule, a check, or a script (the **encode-lessons-in-structure** principle skill).

**Reply:** the playbook you designed, the rigor level and why, the decision-trail path, what's verified against the predicate, and what's still open.
