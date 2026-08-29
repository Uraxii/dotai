# Skills

User-level skills, harness-neutral, in the Agent Skills format. Source of truth for every harness; the `raxii-dotai-setup` skill copies them into each harness. Each skill is a directory with a `SKILL.md` (frontmatter + body) plus optional bundled resources.


## Skills

| Skill | Description |
|-------|-------------|
| [caveman](caveman/SKILL.md) | Terse smart-caveman output style; pin in the harness's persistent instructions to keep it on. |
| [domain-modeling](domain-modeling/SKILL.md) | Build and sharpen the project's ubiquitous language; record decisions. |
| [grilling](grilling/SKILL.md) | Interview the user relentlessly about a plan or idea until understanding is shared. |
| [handoff](handoff/SKILL.md) | Compact the current conversation into a durable handoff doc in `$TMPDIR` for another session. |
| [wayfinder](wayfinder/SKILL.md) | Plan work too big for one session as a map of investigation tickets on the tracker; resolve them one at a time. |
| [tdd](tdd/SKILL.md) | Red-green-refactor TDD loop. |
| [prototype](prototype/SKILL.md) | Throwaway prototype to flesh out a design before committing to it. |
| [yeet](yeet/SKILL.md) | Stage + commit + push + open PR in one flow. |
| [write-a-skill](write-a-skill/SKILL.md) | Author new skills with proper structure. |

### Engineering set

| Skill | Description |
|-------|-------------|
| [research](research/SKILL.md) | Investigate against primary sources, clip every cited web page into the knowledgebase, write the findings to a Markdown file. |
| [interrogate](interrogate/SKILL.md) | Adversarial multi-model review of a diff; lead synthesizes a verdict. |
| [blast-radius](blast-radius/SKILL.md) | Find what a change breaks elsewhere before it ships; prove the safety fact by running code. |
| [resolving-merge-conflicts](resolving-merge-conflicts/SKILL.md) | Resolve an in-progress git merge / rebase conflict. |
| [why](why/SKILL.md) | Investigate why code was built this way from source control, tickets, docs, chat, and telemetry; returns a cited, confidence-calibrated read. |
| [how](how/SKILL.md) | Explain how a subsystem works, or critique its architecture with multi-model critics. |

### Orchestration and role skills

| Skill | Description |
|-------|-------------|
| [poteto-mode](poteto-mode/SKILL.md) | The mode for any non-trivial task: triggers, principle index, autonomy, role contract, playbook index. |
| [show-me-your-work](show-me-your-work/SKILL.md) | Keep a reviewable TSV decision trail for long-running or unattended work, cross-model reviewed at the end. |
| [setup-models](setup-models/SKILL.md) | Interview the user role by role, then rewrite the poteto-mode model map. |
| [principle-code-quality](principle-code-quality/SKILL.md) | Cross-language standard for writing, reviewing, and refactoring code, with per-language references. |
| [architect](architect/SKILL.md) | Settle system structure and author the code skeleton before any logic is written. |
| [requirements-clarifier](requirements-clarifier/SKILL.md) | Turn a vague task into user stories, acceptance criteria, and edge cases. Read-only. |
| [arena](arena/SKILL.md) | Fan out N parallel candidates at the same task, pick a base, graft in the best of the losers. |
| [swarm](swarm/SKILL.md) | Fan out N parallel workers, drain them, return one consolidated report. |
| [figure-it-out](figure-it-out/SKILL.md) | Design an auditable playbook for a large migration or ambitious change when no narrower one fits. |

### Principle skills

| Skill | Description |
|-------|-------------|
| [principle-laziness-protocol](principle-laziness-protocol/SKILL.md) | Deeper subtraction pass when a diff keeps growing layers, wrappers, and options. |
| [principle-never-block-on-the-human](principle-never-block-on-the-human/SKILL.md) | Proceed on reversible work instead of stopping to ask permission. |
| [principle-prove-it-works](principle-prove-it-works/SKILL.md) | Observe the real artifact before declaring anything done. |
| [principle-guard-the-context-window](principle-guard-the-context-window/SKILL.md) | Route bulk output to subagents and keep only summaries in the main thread. |
| [principle-encode-lessons-in-structure](principle-encode-lessons-in-structure/SKILL.md) | Turn a rule that keeps recurring into a mechanism, then delete the prose. |
| [principle-foundational-thinking](principle-foundational-thinking/SKILL.md) | Pick the core data shape and the order of work before writing logic. |
| [principle-outcome-oriented-execution](principle-outcome-oriented-execution/SKILL.md) | Converge on the target architecture instead of shimming every intermediate commit green. |
| [principle-experience-first](principle-experience-first/SKILL.md) | Spend effort where the consumer feels it, and cut surface area to keep the core tight. |
| [principle-exhaust-the-design-space](principle-exhaust-the-design-space/SKILL.md) | Compare two or three competing prototypes side by side before committing. |
| [principle-redesign-from-first-principles](principle-redesign-from-first-principles/SKILL.md) | Rebuild the design as if the new requirement had been known on day one. |
| [principle-build-the-lever](principle-build-the-lever/SKILL.md) | Build the codemod, script, or generator instead of doing non-trivial work by hand. |

### Prose and session management

| Skill | Description |
|-------|-------------|
| [unslop](unslop/SKILL.md) | Cut AI tells and shape register, format, and length of any writing. |
| [technical-writing](technical-writing/SKILL.md) | Layered technical-writing standard: Diátaxis, Google style, STE, Global English. |
| [rotate-agent](rotate-agent/SKILL.md) | Rotate a bloated long-running subagent into a fresh one via a transient handoff doc. |
| [teach](teach/SKILL.md) | Embody a domain-expert teacher and build tracked learning material. |
| [excalidraw-diagrams](excalidraw-diagrams/SKILL.md) | House standard for Excalidraw diagrams, including Obsidian-embedded ones. |

### Godot and demo work

| Skill | Description |
|-------|-------------|
| [godot-headless-cli](godot-headless-cli/SKILL.md) | Drive Godot 4.x from the shell without opening the editor. |
| [godot-playtest](godot-playtest/SKILL.md) | Drive a running Godot game through godot-mcp to verify a change in-game. |

### Tools and integrations

| Skill | Description |
|-------|-------------|
| [agent-workbench](agent-workbench/SKILL.md) | One CLI over the knowledgebase vault, bd board hub, and artifact review service. |
| [proton-pass-cli](proton-pass-cli/SKILL.md) | Retrieve credentials from Proton Pass via pass-cli. |
| [azure-devops](azure-devops/SKILL.md) | Read-only queries against Azure DevOps repos, pipelines, and work items. |
| [cloudflare](cloudflare/SKILL.md) | Query Cloudflare zones, DNS exposure, rulesets, WAF posture, and Workers routes. |
| [snyk](snyk/SKILL.md) | Query the Snyk REST API for projects, targets, and issues. |
| [sysdig](sysdig/SKILL.md) | Query Sysdig Secure for runtime vulnerability posture and secure events. |
| [ox-security](ox-security/SKILL.md) | Query OX Security as a connector aggregator for issues, apps, and repo-to-runtime paths. |

### Archived

| Skill | Description |
|-------|-------------|
