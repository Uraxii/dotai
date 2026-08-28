# Authoring or modifying a skill

Pick when: writing or changing a skill. You own the skill's voice.
Agent-facing prose has a higher bar than human prose; an unhelpful sentence
becomes an instruction.

1. Load `write-a-skill`. It owns structure and progressive disclosure.
2. Validate: frontmatter has `name` and `description`, referenced files exist,
   cross-skill links resolve.
3. Test cases if structural; skip if subjective.
4. Run Opening a PR (`roles/opening-a-pr.md`).

When in doubt, delete. Prose earns its keep by changing a decision. Tell it to
do the thing, skip the reason. Explain only when the rule is confusing without
one. Match tone to scope. Point at structural sources (types, READMEs,
config); hardcoded detail goes stale
(`principle-encode-lessons-in-structure`). Delegate to other skills by path.
Workflow you keep hitting but not captured -> propose a new skill.

**Reply:** skill summary, key design decisions, validation notes.
