---
name: write-pr
description: Create or refresh reviewer-facing PR titles and descriptions. Use when opening a PR, updating its title or body, or preparing branch changes for review.
---

# Write PR

Write the PR body as a cover note for reviewers, not a changelog, validation log, or file-by-file summary.

## Inspect the Change

Requires authenticated `gh` 2.99 or later. Inspect the current branch, working
tree, PR, base branch, commits, and full diff:

```bash
git branch --show-current
git status --porcelain
gh pr view --json number,title,body,url,baseRefName,headRefName
gh repo view --json defaultBranchRef
```

If `gh pr view` reports that no PR exists, continue with first-time PR
creation. For an existing PR, use its `baseRefName`; otherwise use the
repository default branch. Set `BASE`, then inspect:

```bash
git log "$BASE"..HEAD --oneline
git diff "$BASE"...HEAD
```

If on `main` or `master`, create a feature branch first. Ensure intended
changes are committed and review the whole branch diff, not only the latest
commit or existing PR text.

## Pick the Template

Use the repo's PR template. If it has several, pick the one that fits the
change. If it has none, use [default-template.md](references/default-template.md).

Keep required sections. Fill optional sections only when they help the
reviewer.

Project instructions (CLAUDE.md, AGENTS.md, CONTRIBUTING.md) override this
skill.

## Core Rules

- Run `/deslop` over the diff before commit,
- Run `/no-comments` before review.
 - Write every PR title, PR description, and commit body with `/technical-writing`, then apply `/unslop`.
 - Apply every technical-writing layer except Diátaxis. Use one word for each action, keep articles, and avoid `-ing` when a plain verb works.
- Describe concrete changed behavior, affected surfaces, and reviewer impact
  before implementation detail.
- Explain motivation, risk, tradeoffs, migration, or review focus only when
  useful.
- Use the smallest structure that makes the change easier to review.
- Replace internal prompt or process terminology with specific behavior.
- When refreshing a PR, rewrite around the current full diff without narrating
  review history.
- Show behavior, not settings. Prove a setting works; do not list its value.
- Write "Done when" items a reviewer can see or run.
- Cover every role and variant the change affects in "Try it", with what the
  reviewer should see.

## Titles

Use `<type>(<scope>): <subject>` or `<type>: <subject>`.

Allowed types: `feat`, `fix`, `ref`, `perf`, `docs`, `test`, `build`,
`ci`, `chore`, `style`, `meta`, `license`, and `revert`.

- Describe the dominant full-branch change with the narrowest accurate type
  and scope.
- Use `!` only when the change breaks an external contract, and explain the
  affected surface in the body.
- Avoid vague subjects such as `update`, `cleanup`, `misc`, `fix stuff`, or
  `address feedback`. Do not add a trailing period.
- Keep an existing title only when it still describes the whole diff.

## Body Shape

Choose the minimum useful shape:

| Change | Include |
|--------|---------|
| Small or obvious | One concise paragraph without headings. |
| Feature, bug fix, or refactor | Changed behavior and effect; add root cause, unchanged behavior, or non-obvious approach when relevant. |
| Contract or breaking change | Affected API, schema, payload, config, permission, storage, or CLI surface; include compatibility and migration guidance. |
| Operational, visual, or workflow change | User/operator effect, measured impact, failure modes, or flow when useful. |
| Broad, generated, or cross-cutting change | Organizing principle, why the breadth is necessary, and where review should start. |

For review-feedback updates, describe the resulting PR as a whole rather than
the sequence of revisions.

## Reviewer Aids

Use an aid only when it reduces reviewer reconstruction work:

- A compact before/after or interface example for changed contracts.
- A small Mermaid diagram for async flows or state transitions.
- A screenshot or recording when visual evidence exists.
- A rollout, compatibility, risk, or review-order note when reviewers or
  adopters need it.

Introduce an artifact with one sentence explaining what reviewers should
notice. Omit it when prose is clearer.

Attach media with `--attach` and reference it as `![alt](./file.webp)`; `gh`
replaces the path with the uploaded URL. Put each video on its own line.
Keep every attachment under 10 MB. Prefer WebP for images and WebM
or MP4 for video. If an upload fails, stop and tell the user.

## Boundaries

- Do not add default `Summary`, `Changes`, or `Test Plan` sections.
- Omit routine validation unless it changes risk assessment or explains
  meaningful regression coverage. For docs, skills, copy, or config changes,
  omit it by default.
- Do not paste commands, CI logs, validation dumps, commit logs, placeholders,
  or exhaustive file lists.
- Do not reference anything a reviewer cannot open from the PR page: local or
  relative paths, external image hosts, agent sessions, or reviews and runs
  that left no trace on the PR.
- Never include customer or organization names, user emails, support ticket
  contents, secrets, or PII.
- Use issue references only when verified from user input, branch names,
  commits, PR discussion, or tracker output. `Fixes <issue>` closes;
  `Refs <issue>` only links.
- Link each known limit to an issue.

## Create or Update

Create new PRs as drafts. Write the body to a temporary Markdown file, then run:

```bash
gh pr create --draft --title '<title>' --body-file /tmp/pr-body.md --attach ./after.webp
```

When the PR is ready for the user to view, convert it from a draft:

```bash
gh pr ready PR_NUMBER
```

Update existing PRs:

```bash
gh pr edit PR_NUMBER --title '<title>' --body-file /tmp/pr-body.md --attach ./after.webp
```

Refresh the title and body when follow-up commits materially change scope,
approach, breaking behavior, risk, migration, or review expectations. Skip
typo-only, formatting-only, and rename-only follow-ups.

## Examples

Small change:

```markdown
The AI Customizations section now starts collapsed so it does not consume
sidebar space before users need it. Expanding it preserves the existing saved
preference behavior.
```

Breaking contract:

````markdown
Run logs now emit chunk-level records instead of one skill-level record.
Consumers that read top-level `findings` must iterate over
`chunk.findings` for each record.

Before:

```json
{"skill": "security-review", "findings": [...]}
```

After:

```json
{"schemaVersion": 1, "chunk": {"index": 1, "findings": [...]}}
```
````
