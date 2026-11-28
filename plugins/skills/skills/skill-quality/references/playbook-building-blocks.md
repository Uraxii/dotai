# Playbook building blocks

A playbook is a skill, or a file in a skill, that holds numbered steps for one
procedure. A router is an entry file that sends each request to one playbook.
Use this file to choose between the two, to name the blocks a playbook uses,
and to word each block.

## Contents

- [Regular skill or router](#regular-skill-or-router)
- [Route lines](#route-lines)
- [Core blocks](#core-blocks)
- [Optional blocks](#optional-blocks)
- [Compose a playbook](#compose-a-playbook)
- [Update a playbook](#update-a-playbook)

## Regular skill or router

Write a router skill when one of these is true:

- The skill holds four or more procedures, and only one applies to a request.
- Ten or more sibling skills share one topic, and their descriptions overlap.
- The skill listing drops descriptions. Claude Code and Codex cut descriptions
  when the listing is over its budget.

A router also needs both of these:

- Each procedure is complete without the others.
- A test set of prompts reaches the correct route in 80% of cases or more.
  RouterBench found that a router degrades fast above a 0.2 error rate.

Write a regular skill when one of these is true:

- The skill has one to three procedures.
- One task usually needs several procedures together. A router that picks one
  loses the others.
- Every run needs all of the text.

LangChain's multi-agent benchmark found that a single agent beat a supervisor
when only one other domain was present.

## Route lines

- Start each route with the words that a user says, not a summary of the
  procedure.
- Give each route one condition.
- Add a "Not X, see Y" line for each near neighbor.
- State which route wins when two routes match.
- Give one default route for a request that matches no route.
- Keep each procedure file one level below the entry file.
- Point to the procedure file. Do not restate its content. A router that
  restates a procedure loses detail, as the LangChain supervisor did.

## Core blocks

Each playbook uses all of these. Each entry gives when to use the block, a
wording pattern, the fields the block needs, and the source.

### Trigger

- When: every playbook and every route.
- Wording: `Use for "<user words>". Not for <near miss>; see <other>.`
- Fields: the words a user says, and one near miss.
- Source: Anthropic skill authoring guide.

### Deliverable

- When: every playbook. Name the artifact before the first step.
- Wording: `The deliverable is <artifact>, not <thing it is mistaken for>.`
- Fields: the artifact, and what does not count.
- Source: SOP-Bench, where agents finished with the wrong output; MAST, where
  11.8% of failures disobeyed the task specification.

### Step with expected state

- When: every step.
- Wording: `<N>. <Verb> <object>. Expect <observable state or value>.`
- Fields: one action, and the state after it. "Done" is not a state.
- Source: Degani and Wiener checklist study, guideline 4; Agent Workflow
  Memory, where each step records the state it leaves.

### Gate

- When: a step must not start until a condition holds.
- Wording: `Before step <N>, run <check>. If it fails, <stop or route>.`
- Fields: a check that can run, and the route on failure.
- Source: SOPBench, where a verdict without a check did not give compliance;
  Anthropic "Building effective agents".

### Verify

- When: the playbook changes or produces something.
- Wording: `Verify on <real artifact>: <check>. A proxy is not a pass.`
- Fields: the real artifact, the check, and the pass condition.
- Source: MAST, where an added verification step gave +15.6%.

### Stop predicate

- When: every playbook. Loops and long runs need it most.
- Wording: `Done when <predicate a reader or script can check>.`
- Fields: one checkable predicate.
- Source: MAST, where 12.4% of failures did not know when to stop; NASA PRL,
  where each step declares how it exits.

### Pause or escalate

- When: a step is irreversible, or needs a decision only a person can make.
- Wording: `Pause before <step>. Show <evidence>. Ask <who> to <decide>.`
- Fields: the trigger, the person, and what to show them.
- Source: surgical safety checklist study, with fixed pause points; AWS SSM
  Automation `aws:approve`; CACAO manual commands.

### Reply contract

- When: every playbook. Make it the last line.
- Wording: `**Reply:** <item>, <item>, <item>.`
- Fields: each item the reply must hold.
- Source: Degani and Wiener checklist study, guideline 6, where the completion
  call is the last item.

## Optional blocks

Use a block only when the procedure needs it.

### Branch

- When: the next step depends on a result.
- Wording: `If <one condition>, go to step <N>. Otherwise, go to step <M>.`
- Fields: one atomic condition, and both arms.
- Source: SOP-Agent, where compound and/or conditions caused wrong branches;
  FlowBench.

### Bounded loop

- When: a step repeats until a result.
- Wording: `Repeat steps <N> to <M> at most <K> times, until <predicate>. After <K>, escalate.`
- Fields: the cap, the predicate, and the route after the cap.
- Source: AWS SSM Automation `aws:loop`, with MaxIterations; AFlow, with a
  retry cap of 3.

### Parallel

- When: two or more units share no files or state.
- Wording: `Run <A> and <B> in parallel. Join when both report <result>.`
- Fields: the independent units, and the join condition.
- Source: CACAO `parallel`; Anthropic "Building effective agents".

### Delegate

- When: a worker does a unit of the procedure.
- Wording: `Give <worker> the goal, the files in scope, and the done check.`
- Fields: goal, scope, done check, and the form of the report.
- Source: Anthropic "Building effective agents", orchestrator-workers.

### Baseline

- When: the playbook claims to improve a result.
- Wording: `Before the change, record <measure> without it.`
- Fields: the measure, and where the record goes.
- Source: Anthropic skill authoring guide; Anthropic skill best practices,
  which say to build evaluations first.

### Independent review

- When: an error is costly, or the author cannot see their own mistakes.
- Wording: `A reviewer who did not write <artifact> checks it against <criteria>.`
- Fields: the reviewer, the artifact, and the criteria.
- Source: MAST, where incorrect verification caused 9.1% of failures.

### Forbidden shortcuts

- When: a known shortcut passes the check but misses the goal.
- Wording: `Do not <shortcut>, because <reason>.`
- Fields: the shortcut, and the reason.
- Source: SOPBench, where plain adversarial instructions made agents skip the
  procedure; Anthropic skill authoring guide, which says to explain the why.

### Failure handler

- When: a step can fail and leave partial state.
- Wording: `If step <N> fails, <roll back or recover>, then <stop or continue>.`
- Fields: the recovery, and the next route. A state change also gets a dry run.
- Source: Ansible `rescue`, `always` and check mode; AWS SSM Automation
  `onFailure`.

### Wait

- When: a step depends on an outside event.
- Wording: `Wait until <condition>, at most <time>. Then <route>.`
- Fields: the condition, the time limit, and the route after it.
- Source: NASA PRL Wait; AWS SSM Automation `aws:waitForAwsResourceProperty`.

### Skip-with-reason

- When: a step does not apply to some runs.
- Wording: `Skip step <N> when <condition>. Record "skip: <reason>".`
- Fields: the condition, and the recorded reason.
- Source: Ansible `when`, which reports each skipped task.

### Decision log

- When: the run is long, or a person reviews it later.
- Wording: `Log each decision: what, why, evidence, result.`
- Fields: the four columns, and the log path.
- Source: ACE and ExpeL, which keep an itemized record of what worked.

### Checkpoint

- When: the run can stop partway and resume in a new session.
- Wording: `After step <N>, write <state> to <file>.`
- Fields: the state, and the file.
- Source: StateFlow, which keeps the current state apart from the step
  content; Anthropic skill best practices, with a checklist to copy and track.

## Compose a playbook

An agent can write a playbook only behind these checks. SkillsBench measured
skills that agents wrote for themselves at 8.1 to 11.5 points below the
baseline with no skill.

1. Run the task without the playbook, and record the failure. If no failure
   occurs, do not write the playbook.
2. Use [Regular skill or router](#regular-skill-or-router) to choose the
   kind of skill.
3. Start from the nearest template in `examples/`. Each template has
   `shape: playbook` or `shape: router` in its frontmatter. In a `SKILL.md`,
   put the `shape:` line under `metadata:`.
4. Name each building block that each step uses.
5. Run `scripts/checks/playbook-shape.sh` on the skill directory. Expect no
   FAIL.
6. Test the description, or the route lines of a router. Write about 20
   queries. Half must trigger and half must not. Make the negative queries
   near misses. Use 60% of the queries to tune and 40% to test. Select the
   wording by the test score. Stop after 5 rounds.
7. Run a paired test: the same prompts with the playbook and without it.
   Give each assertion a descriptive name, and make each one objective. Flag
   each assertion that passes in both runs, because it does not measure the
   playbook.
8. Ask a person to approve the playbook before release.

To update a skill that exists, keep its name. Copy the old version first, and
use the copy as the baseline in step 7. The Anthropic skill authoring guide
uses the same trigger test and paired test.

## Update a playbook

Edit one step at a time. Never rewrite the whole file. ACE measured a context
that fell from 18,282 tokens to 122 after a full rewrite.
