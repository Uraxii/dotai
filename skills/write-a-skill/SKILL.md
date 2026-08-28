---
name: write-a-skill
description: Create new agent skills with proper structure, progressive disclosure, and bundled resources. Use when user wants to create, write, or build a new skill.
---

# Writing skills

## Structure

```
skill-name/
├── SKILL.md           # required
├── references/*.md    # detail SKILL.md points at but does not state
└── scripts/           # deterministic operations
```

Frontmatter carries `name` and `description`, nothing else. Body opens with the
rules, not a restatement of the description.

## Description

The description is the only thing an agent sees when deciding whether to load
the skill, listed beside every other installed skill. It must answer two
questions: what capability this gives, and what triggers it (keywords,
contexts, file types).

Max 1024 chars, third person. First sentence what it does, second "Use when
[specific triggers]".

Good: `Extract text and tables from PDF files, fill forms, merge documents. Use
when working with PDF files or when user mentions PDFs, forms, or document
extraction.`

`Helps with documents.` gives the agent no way to pick this over any other
document skill.

## What earns a line

Every section is a rule the agent could not derive. Cut on sight: sections
restating the description, "when to use" blocks, checklists restating the body,
output templates longer than the rule they serve, worked examples repeating a
stated rule, provenance prose, and anything a task brief already carries.

A rule stated in two skills has one home. Point at it from the other.

## Scripts

Add one when the operation is deterministic (validation, formatting), when the
same code would otherwise be generated repeatedly, or when errors need explicit
handling. Scripts save tokens and beat generated code on reliability.

## Splitting

Keep SKILL.md under 500 lines. Overflow goes into `references/`, one level deep,
never deeper. A reference file survives only when SKILL.md points at it for a
rule SKILL.md does not itself state. No time-sensitive information anywhere.
