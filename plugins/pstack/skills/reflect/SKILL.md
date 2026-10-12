---
name: reflect
description: Spawn three parallel review subagents over the active transcript, surface learnings, and route each to a concrete edit on an existing skill. Use when the user says reflect.
disable-model-invocation: true
---

# Reflect

Mine the current conversation for durable learnings, then route them into skill edits.

## When to invoke

Invoke when the user says "reflect" or "/reflect". Skip when the conversation is trivial, off-topic, or already covered by an existing skill the parent followed correctly. One-offs are not learnings.

## Process

### 1. Locate the active transcript

Resolve an explicit active-project transcript source, exported conversation, or supplied digest. Use only that scope. Report missing transcript evidence if no source resolves. Never scan another project's content.
Check the session ID or opening user prompt in the source's actual format.
If no path resolves, write a digest and record its evidence limits.

### 2. Spawn three reviewers in parallel

One message, Spawn three reviewers through the supported agent API. Use the model roles below. Forbid writes and grant the required connector access. Reviewers need MCP access for context lookups (tickets, chat threads, observability traces referenced in the transcript). Verify that the worker can reach the required connectors.

Each reviewer and the synthesizer name a role in `models.json`, two directories up from this skill's directory. Use the first name in your harness's list for that role. The [Models section of `poteto-mode`](../poteto-mode/SKILL.md#models) tells how to find the file, how the override sheet changes a role, and what to do when the harness rejects a name.

| Lens | Role | Prompt template |
|---|---|---|
| Judgment | `reflect judgment, divergent, synthesizer` | `references/judgment-reviewer.md` |
| Tooling | `reflect tooling` | `references/tooling-reviewer.md` |
| Divergent | `reflect judgment, divergent, synthesizer` | `references/divergent-reviewer.md` |

Pass each template verbatim, substituting the transcript path or digest where marked. Reviewers return findings in the agent API response body.

### 3. Synthesize

Spawn one synthesizer through the supported agent API. Use the `reflect judgment, divergent, synthesizer` model role. Forbid writes and grant required connector access. The synthesizer's quality check includes spot-verifying citations, which can require MCP access. Verify that the worker can reach the required connectors. Use `references/synthesizer.md` verbatim, with each reviewer's full output inlined where marked. The synthesizer returns a structured Accepted / Rejected / Backlog list.

### 4. Structural enforcement check

Sanity-check the synthesizer's Accepted list. For any item that would be enforced more reliably by a lint rule, script, metadata flag, or runtime check, move it from Accepted to Backlog. See the **encode-lessons-in-structure** principle skill.

### 5. Apply

Before applying any Accepted edit, present the synthesizer's full Accepted/Rejected/Backlog output to the user and wait for explicit approval. The user picks which subset to apply and may redirect routings. Skill changes affect every future agent in the org. Do not auto-apply.

Backlog items file to whatever devex / backlog tracker your team uses automatically. Only the Accepted list waits for approval.

For each approved Accepted item, follow the Routing field exactly:

- Trivial existing-skill edit (a one-line bullet, a tightened sentence, a stale fact corrected): parent does directly.
- Substantive existing-skill edit (a new section, a new pattern table, more than ~10 lines): hand to your harness's skill-authoring guidance and run its draft / test / iterate loop.
- `tune description: <skill path>` (the skill exists but didn't trigger when it should have): use your harness's skill-authoring guidance and run its description-optimization loop.
- `new skill via authoring guidance: <kebab-name>`: use your harness's skill-authoring guidance. Do not invent the shape ad hoc.

If your environment ships a SKILL.md validator, run it on every touched skill before declaring done. Skip this step if it doesn't.

### 6. Summarize for the user

Short list, no preamble:

- Edits applied: `<skill path>`. What changed, one line each.
- New skills created: `<skill path>`. One line each (rare).
- Backlog filed to the devex tracker: `<issue title>` (`<tags>`). One line each.
- Dropped: one line per rejected finding + reason from the synthesizer.

Use [Platform adaptation](../poteto-mode/references/platform-adaptation.md) for tool APIs, skill locations, and evidence limits.
