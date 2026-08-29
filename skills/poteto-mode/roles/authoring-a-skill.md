# Authoring or modifying a skill

Pick when: writing or changing a skill. You own the skill's voice.
Agent-facing prose has a higher bar than human prose; an unhelpful sentence
becomes an instruction.

1. Structure: frontmatter carries `name` and `description` only; the body
   opens with rules, not a restatement; bulk goes to `references/` files
   loaded on demand; the description is the only text an agent sees when
   deciding to load, so it names the situations, not the contents.
2. Validate: frontmatter has `name` and `description`, referenced files exist,
   cross-skill links resolve, no em-dashes, lines reflowed to 80 columns.
3. Test cases if structural; skip if subjective.
4. Run Opening a PR (`roles/opening-a-pr.md`).

When in doubt, delete. Prose earns its keep by changing a decision. Tell it to
do the thing, skip the reason. Explain only when the rule is confusing without
one. Match tone to scope. Point at structural sources (types, READMEs,
config); hardcoded detail goes stale
(`principle-encode-lessons-in-structure`). Delegate to other skills by path.
Workflow you keep hitting but not captured -> propose a new skill.

**Reply:** skill summary, key design decisions, validation notes.
