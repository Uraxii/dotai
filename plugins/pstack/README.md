# pstack

pstack is a set of skills and named agents for coding agents. It has four parts: principles, playbooks, roles, and skills. This document explains each part, how the parts connect, and which part to change. Read it before you design a change to pstack.

To add, remove, or rename a part, also follow [CONTRIBUTING.md](CONTRIBUTING.md).

## Principles

**What it is.** Each principle is a skill with the name `principle-<name>`, in `skills/principle-<name>/SKILL.md`. A principle holds one rule of engineering judgment. It has these items:

- The trigger: the situation where the rule applies, for example "when debugging".
- The rule: what to do, for example "trace each symptom to its root cause and fix it there".
- The reason for the rule.
- A pattern of concrete actions.

**Its function.** A principle tells an agent how to decide well. It does not tell the agent which steps to do, or in which order. Playbooks and roles cite principles. They do not repeat them. Thus one rule has one home, and each agent that applies the rule uses the same text. An agent reads the principle in full before it applies it, and names the principle that shaped each decision. The Principles index in `skills/poteto-mode/SKILL.md` lists each principle with its trigger.

**When a change goes here.** Add a principle when the change is "how to judge X well". A principle is not correct for "when to do X" (a playbook step) or for "who does X" (a role).

Example: `principle-skeptically-review` tells how to examine a design or a diff, how to sort the findings, and when to fail the review. The Feature playbook says when the review occurs. `skeptic-reviewer` is the agent that does it.

## Playbooks

**What it is.** Each playbook is the procedure for one type of task, for example a feature, a bug fix, or a prototype. Playbooks are in `skills/poteto-mode/playbooks/`. A playbook lists the steps in order, the gates (for example the skeptic review), and the reply at the end.

**Its function.** The agent that picks the playbook runs it. That agent copies the steps into its todo list, spawns a role for each delegated step, gets the gate results, and decides what to do with them. A playbook says when and in which order. It cites principles for judgment and roles for the work.

**When a change goes here.** Add or change a playbook step when the change is "do X at this point in this type of task".

## Roles

**What it is.** Each role is a named alias for a poteto agent, in `agents/<role>.md`. Examples are `architect`, `developer`, `skeptic-reviewer`, and `tester`. A role does one type of step. Its agent file tells:

- What the role does.
- What the role must not do. For example, `skeptic-reviewer` edits no file.
- What the role reads.
- What the role returns.

A role preloads, in its frontmatter, the principles and skills that it always needs. A Codex variant, for example `skeptic-reviewer-codex`, is the same role with the steps that are necessary to run it through Codex.

**Its function.** A role gives one type of step to a separate agent with a known scope.

**When a change goes here.** Add a role when the change is "a different agent must do X". The usual reason is separation: the author does not review its own work.

## Skills

**What it is.** Each skill is a workflow or a tool instruction, in `skills/<name>/SKILL.md`. An agent loads a skill when it needs it. Examples:

- `architect` makes a design sketch.
- `write-pr` writes a PR description.
- `track-work` uses the beads plugin to track work.
- `index-the-codebase` indexes code with codebase-memory.

**Its function.** A playbook step or a role names the skill. The skill tells how to do the task.

**When a change goes here.** Add a skill when the change is "how to do X", and X is a reusable task or tool use. A judgment rule is a principle, not a skill.

## How the parts connect

`skills/poteto-mode/SKILL.md` is the entry point. It lists the playbooks, the principles, and the triggers that load each skill.

Example: a feature.

1. The agent matches the task to the Feature playbook (`skills/poteto-mode/playbooks/feature.md`) and copies its steps into its todo list.
2. A step runs the `architect` skill, which makes a design sketch.
3. The playbook requires a skeptic review of the sketch. The agent spawns the `skeptic-reviewer` role.
4. `skeptic-reviewer` preloads `principle-skeptically-review` and applies it to the sketch. It returns pass or fail.
5. On a fail, the agent sends the objections back to the author of the sketch. On a pass, implementation starts. The new code then gets a second skeptic review in the same way.

The playbook owns the order. The role owns the work. The principle owns the judgment. The skill owns the procedure.

## Which part to change

| Change | Part | Example |
|---|---|---|
| A new rule of judgment | A principle | A new review rule goes into `principle-skeptically-review`, or into a new `principle-<name>`. |
| A new step in a type of task | A playbook | A new step in bug fixing goes into `playbooks/bug-fix.md`. |
| A new agent for a type of step | A role | A new agent file in `agents/`. |
| A new tool or a reusable procedure | A skill | A new `skills/<name>/SKILL.md`. A playbook step or a role names it. |
