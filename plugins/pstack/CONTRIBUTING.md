# Contributing to pstack

`skills/poteto-mode/SKILL.md` is the inventory of pstack. Agents pick playbooks, roles, skills, and principles from it. [README.md](README.md) tells which sections the inventory has.

Update the inventory in the same commit when you do one of these changes:

- Add, remove, or rename a playbook, a role, a skill, or a principle.
- Change the trigger of a principle or a skill, or the type of task that a playbook is for.
- Change what a role or a skill does, or its frontmatter `description`.

The inventory must agree with the contents of these directories:

- `skills/poteto-mode/playbooks/` for playbooks.
- `agents/` for roles.
- `skills/` for skills and principles.

Also update each reference to an old name. Then run `scripts/check` from the repository root. No check compares the inventory with the directories, so compare them yourself.

To find the correct part for a change, read [README.md](README.md).
