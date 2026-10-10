# Contributing to pstack

`skills/poteto-mode/SKILL.md` is the inventory of pstack. Agents pick playbooks, roles, skills, and principles from it.

When you add, remove, or rename a playbook, a role, a skill, or a principle, update the inventory in `skills/poteto-mode/SKILL.md` in the same commit. The inventory must agree with the contents of these directories:

- `skills/poteto-mode/playbooks/` for playbooks.
- `agents/` for roles.
- `skills/` for skills and principles.

Also update each reference to an old name. Then run `scripts/check` from the repository root.

To find the correct part for a change, read [README.md](README.md).
