---
name: how
description: "Use for \"how does X work\", rich explanations of a code change, diff, branch, or PR, code walkthroughs before changing something, and placement / ownership / layering questions (\"where should this live\", \"which package owns this\", \"is this the right layer\"). Explains subsystem architecture, runtime flow, and changes in chat, HTML, or native Notion. Can critique architecture. Use why for motivation."
---

# How

Explore the codebase to answer "how does X work?" questions. Produce clear architectural explanations at the level of a senior engineer onboarding onto a subsystem. Enough to build a working mental model, not annotated source code.

Three modes:

1. **Explain** (default). Explore the codebase and produce a clear explanation
2. **Critique.** Explain first, then spawn multiple models to independently identify architectural issues
3. **Change walkthrough.** Explore the existing system and the specified
   change, then teach it through Background, Intuition, Code, and Quiz.

Choose the mode from the request. A diff explanation uses Change walkthrough;
an architectural assessment uses Critique. A request for both uses the
Critique workflow with the change walkthrough outline before the verdict.
Do not add a quiz to ordinary Explain
or Critique output unless requested.

## Output selection

Output is separate from mode. Honor the user's chosen format or an established
preference for this task. Otherwise use chat, including for change walkthroughs
without a requested artifact. For a requested rich artifact with no format
specified, ask whether the user wants HTML or Notion while continuing any
independent exploration.
Resolve the format before creating an artifact or publishing a page.

- **Chat.** Use the mode's outline directly in the reply. For a change quiz,
  keep answers separate from the questions so the reader can attempt them.
- **HTML.** Read [references/html-output.md](references/html-output.md).
- **Notion.** Read [references/notion-output.md](references/notion-output.md).
  This creates native Notion content, with selective HTML where useful.

Read only the selected output reference. Pass the chosen mode, output format,
and applicable references to the agent writing the explanation. Codebase
inspection is read-only; output writing is limited to the selected artifact
or Notion destination. Inspection-only explorers do not publish pages.

## Change walkthrough mode

Read [references/change-walkthrough.md](references/change-walkthrough.md),
then follow Explain Steps 1-4 using that reference's outline instead of the
ordinary Output Format. Resolve the diff scope before exploration and pass
the same comparison to every explorer. This mode owns its comprehension quiz;
it does not require `teach`, a mastery database, or a quiz pass before review.

## Explain Mode

### Step 1. Understand the Question and Assess Complexity

Parse what the user is asking about:

- "How does the rate limiter work?", a subsystem
- "How do we handle billing for on-demand usage?", a feature flow
- "How is the auth service structured?", an architectural overview
- "Walk me through what happens when a user submits a form", a runtime trace
- "Explain this PR in HTML", a change walkthrough with HTML output
- "Explain this diff in Notion", a change walkthrough with native Notion output

Identify the scope. If ambiguous, state your best-guess interpretation before exploring. Don't ask. Let the user redirect if you're off.

Exceptions: resolve material diff ambiguity as the change reference directs,
and missing artifact choices as the output instructions direct.

**Assess complexity to decide the approach:**

- **Simple** (a single module, a small utility, a narrow question like "how does function X work"): skip explorer agents; the explainer explores and explains in a single pass. Go to Step 2b.
- **Complex** (a subsystem spanning multiple files/services, a cross-cutting feature, a full architectural overview): spawn parallel explorer agents first, then hand off to the explainer. Go to Step 2a.

When in doubt, lean simple. You can always spawn explorers if the explainer hits a wall.

### Step 2a. Explore (complex questions only)

Decompose the question into 2-4 parallel exploration angles, each a distinct slice of the subsystem so explorers don't duplicate work. Example split for "how does the rate limiter work?":

- Explorer 1: data model and state management
- Explorer 2: request path and enforcement
- Explorer 3: configuration and metrics infrastructure

The right decomposition depends on the question. Use your judgment. Narrow questions: 2 explorers is fine. Broad subsystems: up to 4.

Spawn all explorers in a single message:

- `agent`: `explorer`
- `model`: your configured how-explorer model (default `grok-4.6-fast-xhigh`)
- `readonly`: `true`

Each explorer gets the same base prompt from `references/explorer-prompt.md` plus a specific exploration angle naming its slice. Each explorer should:
- If a code indexer is reachable (codebase graph or memory service, graphify,
  similar), query it before any file sweep. Fall back to file search. Return
  `path:line` pointers plus a short conclusion, never file dumps.
- Start broad: file search for relevant directories, text search for key types/interfaces/class names
- Follow the thread: from an entry point, trace the call chain (callers, callees, data flow, type definitions)
- Read the actual code, don't guess from file names
- Stop when it can describe the full path from input to output (or trigger to effect) without hand-waving any step
- Note things that are surprising, non-obvious, or that a newcomer would get wrong

Each explorer returns structured findings: components found, flow traced, files read, anything non-obvious. Overlap between explorers is fine; the explainer reconciles.

Then proceed to Step 3.

### Step 2b. Direct Explain (simple questions)

Explore and explain in one pass, without spawning an explorer. Read
`references/explainer-prompt.md` for the communication style and selected
output instructions. Same structure, just no explorer findings as input.

Proceed to Step 4.

### Step 3. Synthesize (complex questions only)

Once all explorers return, spawn a single explorer agent to synthesize their findings into one coherent explanation:

- `agent`: `explorer`
- `model`: first pinnable name in the `judgment and prose` row of the `poteto-mode` skill's `models.md`; row absent -> omit
- `readonly`: `true`

The explainer gets all explorers' findings and writes the human-facing explanation in the selected mode and output format. Read `references/explainer-prompt.md` for the full prompt template. The explainer reconciles overlapping findings, resolves contradictions, and weaves the slices into a unified picture.

The synthesizer returns the content to the coordinator. It does not create
files or publish pages; the coordinator owns those writes in Step 4.

### Step 4. Present

Present the explainer's output to the user. You may lightly edit for clarity or add context from the conversation, but don't substantially rewrite. The explainer's communication is the product.

For HTML or Notion, the coordinator creates the selected artifact or page,
runs the output reference's verification, and returns the artifact path or
page URL. Report any rendering or publishing limitation.

### Output Format

Follow this structure, adapted to the question. Not every section is needed for every question.

**Overview.** 1-2 paragraphs. What it is, what it does, why it exists. Enough to decide whether to keep reading.

**Key Concepts.** The important types, services, or abstractions. Brief definition of each. Not exhaustive, just the ones needed to understand the rest.

**How It Works.** The core of the explanation. Walk through the flow: what triggers it, what happens step by step, where data goes, the decision points. Prose, not pseudocode. Reference specific files and functions so the reader can go look, but don't dump code blocks unless a snippet is genuinely necessary.

**Where Things Live.** A brief map of the relevant files/directories. Not every file, just the ones needed to start working in this area.

**Gotchas.** Non-obvious or surprising things that would trip someone up. Historical context that explains why something looks weird. Known sharp edges.

## Critique Mode

Triggered when the user asks for architectural issues, problems, or improvements, not just understanding.

### Step 1. Explain First

Run Explain Steps 1-3 before the critics. You must understand the architecture
before critiquing it. Keep the explanation as a draft until the verdict is
ready, then present or publish both together through Step 4.

### Step 2. Spawn Critics

After the explanation is complete, spawn one architectural critic per pinnable model in the `interrogate reviewers` row of the `poteto-mode` skill's `models.md`, all in a single message.

For each critic:
- `agent`: `explorer`
- `model`: one entry from that row.
- `readonly`: `true`

Read `references/critic-prompt.md` for the prompt template. Each critic gets:
1. The explanation from Step 1 (so they don't re-explore)
2. The relevant file paths (so they can read the actual code)
3. The architectural critique rubric from `references/critique-rubric.md`

### Step 3. Lead Judgment

Same framework as the interrogate skill. You're a pragmatic lead, not an aggregator.

Categorize findings:
- **Act on.** Architectural problems worth fixing now
- **Consider.** Real concerns, but the cost/benefit is unclear
- **Noted.** Valid observations, low priority
- **Dismissed.** Wrong, missing context, or style preference

Present the explanation first (from Step 1), then the critique verdict below it. The explanation should stand on its own; someone who just wants to understand the system shouldn't wade through critique.
