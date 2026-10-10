---
name: interrogate
description: "Use for \"interrogate\", \"adversarial review\", \"multi-model review\", \"challenge this\", \"stress test this code\", \"find blind spots\", or \"tear this apart\". Multiple LLM reviewers challenge changes from independent angles."
---

# Interrogate

On Codex, read the [platform mapping](../poteto-mode/references/codex-tools.md), including its per-skill notes, before following this skill.

Spawn one reviewer per configured model to adversarially review code changes. Each model gets the same prompt and rubric. The adversarial signal comes from model diversity, not assigned personas.

The deliverable is a synthesized verdict. Do NOT auto-apply changes.

## Step 1, Determine Scope

Identify what to review from context:

- If the user points at specific files or a diff, use that
- If on a feature branch, run `git diff main...HEAD` (or the appropriate base branch) for the full changeset
- If the user's message references recent work, gather the relevant files

Package the diff (or file contents) plus any surrounding context files the reviewers need to understand the code.

If a bead ordered a design review, look for an open review bead that blocks it: `bd dep list <ordering bead>`, then the open entry whose title starts with `Interrogate:`. If one exists, this is a later round. Read its comments (`bd comments <review bead>`) and append to the package, under an "Earlier findings" heading, the last round's Act On and Consider findings plus every earlier finding still marked `still open`, followed by the author's last `response to round <n>` comment. Reviewers check each earlier finding against that response first and still review the whole package.

## Step 2, State the Intent

Before spawning reviewers, state the intent explicitly. Derive this from:

- The user's message
- Commit messages
- PR description if one exists
- The code itself

Write one clear paragraph. If you're unsure about the intent, ask the user before proceeding.

## Step 3, Spawn Reviewers

Launch all reviewers in a single message using the `Agent` tool. Take the `interrogate reviewers` list from your harness's override sheet (see `setup-pstack`) when it has a row, otherwise from that role's entry for your harness in `plugins/pstack/models.json` (see [Models](#models)). A design review that a bead ordered (Step 6) spawns only the first entry, as Reviewer A. Every other run spawns one reviewer per entry, in order, labelling them Reviewer A, B, C, D as far as the list runs: the list length sets the reviewer count. The panel is only as adversarial as it is model-diverse, so keep the entries from different model families where the harness offers them.

For each reviewer:
- `subagent_type`: `general-purpose`
- `model`: this reviewer's entry from that list
- `readonly`: `true`

If a model slug is rejected as unresolvable when you try to spawn the subagent, check the valid slugs in the Agent tool's error message, pick the closest equivalent (prefer the highest-reasoning tier of the same family), spawn with the valid slug, and open a separate PR to update the configured value or default table. Do not block the review on the slug issue. If the configured value is `inherit-parent` or `auto`, omit `model` instead; never treat those aliases as broken slugs or enter this fallback for them.

Read `references/reviewer-prompt.md` and fill in the template with:
1. The stated intent
2. The diff or file contents
3. The review rubric from `references/rubric.md`
4. The code-quality lens from `references/code-quality-review.md`

The same filled template goes to all reviewers, so every model applies the code-quality lens.

## Step 4, Synthesize

As results come back, build a unified picture:

1. **Parse all findings** from the reviewers
2. **Identify consensus**. Findings raised by 2+ models independently are highest signal.
3. **Identify lone-model findings**. Still worth reading, but weight accordingly.
4. **Deduplicate**. Different models may describe the same issue differently. Merge these and note which models raised it.
5. **Note disagreements**. If one model flags something and another explicitly says the opposite, that's useful context for the verdict.

## Step 5, Lead Judgment

You are the lead reviewer, a pragmatic senior engineer, not a neutral aggregator.

Read `references/lead-judgment.md` for the full framework.

Categorize every finding using these buckets:

- **Act on**. Real issues affecting correctness, security, or maintainability given the actual goals. These would block a real PR.
- **Consider**. Legitimate points, but you're not sure they outweigh the cost of addressing them right now. Worth the user's attention.
- **Noted**. Technically valid but not actionable. Context-dependent, premature optimization, or low-impact given the current stage.
- **Dismissed**. Wrong, nitpicky, or missing context. Brief explanation why.

For each finding, include:
- Which model(s) raised it
- The category (act on / consider / noted / dismissed)
- A one-line rationale for the categorization

## Step 6, Record the Verdict

This step applies only to a design review that a bead ordered. A code review, or a run with no ordering bead, keeps its verdict in chat.

1. If Step 1 found no open review bead, create one that blocks the bead that ordered the work. Until the review closes, the block keeps that bead and its children out of `bd ready` and makes `bd close` on it fail.

   ```sh
   bd create "Interrogate: <subject>" --deps blocks:<ordering bead> --silent
   ```

2. Write the round to a file and add it as a comment (`bd comment <review bead> --file <file>`). The first line is `round <n> at <SHA or artifact>`, where `<n>` is one more than the count of earlier round comments on this review bead. List each Act On and each Consider finding on its own line with its tier, including earlier findings still open. Mark each finding from the previous round `fixed`, `answered: <reason>`, or `still open`. Noted and Dismissed findings stay in the chat verdict.
3. The design's author answers in one comment on the review bead. Its first line is `response to round <n>`. It marks each listed finding `fixed: <change>`, or for a Consider finding, `answered: <reason>`. An Act On finding can only be fixed.
4. If the round had no Act On finding and the response resolves every listed finding, the author closes the review bead: `bd close <review bead> --reason "resolved in <n> rounds"`. If the round had an Act On finding, run interrogate again after the fix, so the next round checks it. Round 3 is the last. If round 3 ends with an Act On finding or an unresolved finding, leave the review bead open and report its open findings to the user.

## Output Format

Present the verdict in this structure:

### Intent
> [The stated intent paragraph from Step 2]

### Reviewers
- Reviewer [label]: [model name], [N findings] (one bullet per reviewer)

### Act On
[Findings that should be addressed. For each: description, which models raised it, why it matters.]

### Consider
[Findings worth thinking about. For each: description, which models raised it, tradeoff involved.]

### Noted
[Valid but low-priority. Brief list.]

### Dismissed
[Rejected findings with brief rationale.]

### Agreement Map
[Where did models agree, where did they diverge, and what does the pattern of agreement/disagreement tell us?]

## Models

Role picks live in the plugin's `models.json`, two directories up from this
skill's own directory (`plugins/pstack/models.json` in the repo). Resolve it
from that directory, not from your working directory. See the Models section
of `poteto-mode` for how each harness learns that path. The file is keyed by
role and then by harness (`claude`, `codex`, `copilot`), each value an
ordered preference list. A spawner reads the entry for its own harness and
pins the first name in it. A row for the same role in your own harness's
override sheet (`~/.claude/pstack-models.md` on Claude Code,
`~/.codex/pstack-models.md` on Codex) wins over it; the sheet's path is its
harness key, so it can only override that harness. See `setup-pstack` to
write one. A role with no override row and no entry for your harness spawns
unpinned: the `Agent` call omits `model` and the child inherits yours.
