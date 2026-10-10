# pstack

pstack is a set of skills and named agents for coding agents. It has four parts: principles, playbooks, roles, and skills. This document explains each part, how the parts connect, and which part to change. Read it before you design a change to pstack.

To add, remove, or rename a part, or to change its trigger or description, also follow [CONTRIBUTING.md](CONTRIBUTING.md).

## The inventory

`skills/poteto-mode/SKILL.md` is the inventory of pstack. Agents pick each part from it. It has these sections:

- Non-negotiables: the triggers that tell an agent when to load a skill or run a step.
- Principles: each principle, with its trigger.
- Skills: each workflow or tool skill, with what it does.
- Roles: each named agent, with what it does.
- Playbooks: each playbook, with the type of task that it is for.

## Principles

**What it is.** A principle is a kind of skill: a skill that holds one rule of engineering judgment. Its name is `principle-<name>`, and it is in `skills/principle-<name>/SKILL.md`. It has these items:

- The trigger: the situation where the rule applies, for example "when debugging".
- The rule: what to do, for example "trace each symptom to its root cause and fix it there".
- The reason for the rule.
- A pattern of concrete actions.

**Its function.** A principle tells an agent how to decide well. It does not tell the agent which steps to do, or in which order. Playbooks and roles cite principles. They do not repeat them. Thus one rule has one home, and each agent that applies the rule uses the same text. An agent reads the principle in full before it applies it, and names the principle that shaped each decision.

**When a change goes here.** Add a principle when the change is "how to judge X well". A principle is not correct for "when to do X" (a playbook step) or for "who does X" (a role).

Example: `principle-skeptically-review` tells how to examine a design or a diff, which objections count, and when to fail the review. It does not say when the review runs.

## Playbooks

**What it is.** Each playbook is the procedure for one type of task, for example a feature, a bug fix, or a prototype. Playbooks are in `skills/poteto-mode/playbooks/`. The Playbooks section of the inventory lists all of them. A playbook lists the steps in order, the gates (for example the skeptic review), and the reply at the end.

**Its function.** The agent that picks the playbook runs it. That agent copies the steps into its todo list, spawns a role for each delegated step, gets the gate results, and decides what to do with them. A playbook says when and in which order. It cites principles for judgment and roles for the work.

**When a change goes here.** Add or change a playbook step when the change is "do X at this point in this type of task". The time when a review, a test, or any other gate runs goes into a playbook, or into the Skeptic review section of the inventory that the playbooks cite. It does not go into a role or a principle.

## Roles

**What it is.** Each role is a named alias for a poteto agent, in `agents/<role>.md`. Examples are `architect`, `developer`, `skeptic-reviewer`, and `tester`. The Roles section of the inventory lists all of them. A role does one type of step. Its agent file tells:

- What the role does.
- What the role must not do. For example, `skeptic-reviewer` edits no file.
- What the role reads.
- What the role returns.

A role preloads, in its frontmatter, the principles and skills that it always needs. The frontmatter can also limit the role's tools.

**Codex variants.** A Codex variant runs the same role through Codex on Claude Code, for example `skeptic-reviewer-codex`. Its agent file has the role's name with `-codex` added. Its body is the shared Codex watcher steps in `skills/poteto-mode/references/codex-watcher-body.md`, which must stay the same in each variant. `hooks/codex_watcher_guard.py` allows a variant only those commands, so a new variant also needs an entry there. `playbooks/delegate-to-codex.md` tells the owner how to brief it.

**Its function.** A role gives one type of step to a separate agent with a known scope.

**When a change goes here.** Add a role when the change is "a different agent must do X". The usual reason is separation: the author does not review its own work.

## Skills

**What it is.** Each skill is a workflow or a tool instruction, in `skills/<name>/SKILL.md`. The Skills section of the inventory lists all of them. Examples:

- `architect` makes a design sketch.
- `write-pr` writes a PR description.
- `track-work` uses the beads plugin to track work.
- `index-the-codebase` indexes code with codebase-memory.

**How a skill loads.** The `description` in the skill's frontmatter tells the harness when to offer the skill. A trigger in the inventory, a playbook step, or a role's frontmatter tells an agent to load it. An agent loads a skill through the `Skill` tool, or reads its `SKILL.md` on a harness without that tool.

**Its function.** The skill tells how to do the task.

**When a change goes here.** Add a skill when the change is "how to do X", and X is a reusable task or tool use. A rule of judgment goes into a principle, which is the kind of skill for judgment.

## How the parts connect

Example: a feature.

1. The agent matches the task to the Feature playbook (`skills/poteto-mode/playbooks/feature.md`) and copies its steps into its todo list.
2. A step runs the `architect` skill, which makes a design sketch.
3. The playbook requires a skeptic review of the sketch. The agent spawns the `skeptic-reviewer` role.
4. `skeptic-reviewer` preloads `principle-skeptically-review` and applies it to the sketch. It returns pass or fail.
5. On a fail, the agent sends the objections back to the author of the sketch. On a pass, implementation starts. The new code then gets a second skeptic review in the same way, and after a pass the agent spawns the `tester` role.

The playbook owns the order. The role owns the work. The principle owns the judgment. The skill owns the procedure.

## Which part to change

| Change | Part | Example |
|---|---|---|
| A new rule of judgment | A principle | A new review rule goes into `principle-skeptically-review`, or into a new `principle-<name>`. |
| A new step in a type of task, or the time when a gate runs | A playbook | A new step in bug fixing goes into `playbooks/bug-fix.md`. |
| A new agent for a type of step | A role | A new agent file in `agents/`. |
| A new tool or a reusable procedure | A skill | A new `skills/<name>/SKILL.md`. A playbook step or a role names it. |

## Checks

Run `scripts/check` from the repository root before you commit. It checks these items:

- `models.json` names only harness keys and models that it can back.
- The generated plugin manifests agree with `scripts/generate-plugin-manifests.py`.
- No committed file has a machine-specific home path.
- Each markdown link in a skill resolves, each skill named in bold or backticks exists in the same plugin, and each `SKILL.md` frontmatter names its own directory and has a description.
- The pytest tests pass.
- The bun tests pass, when bun is installed. Without bun, the stage is skipped locally. CI installs bun and always runs it.

It does not check that the inventory agrees with the directories. [CONTRIBUTING.md](CONTRIBUTING.md) tells you to keep them in agreement.
