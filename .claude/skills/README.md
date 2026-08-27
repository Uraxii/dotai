# Claude Code skills

User-level skills loaded by Claude Code from `~/.claude/skills/`. Each skill is a directory with a `SKILL.md` (frontmatter + body) plus optional bundled resources.

Tree maintained as the Claude Code source of truth. Hermes-equivalent skills live under `.hermes/skills/` with omerxx-style frontmatter; opencode versions under `opencode/skills/`. Edit files directly; no generator.

## Skills

| Skill | Description |
|-------|-------------|
| [caveman](caveman/SKILL.md) | Terse smart-caveman output style; pin via memory for persistent activation. |
| [handoff](handoff/SKILL.md) | Compact the current conversation into a durable handoff doc in `$TMPDIR` for another session. |
| [diagnose](diagnose/SKILL.md) | Disciplined diagnosis loop for hard bugs / perf regressions. |
| [tdd](tdd/SKILL.md) | Red-green-refactor TDD loop. |
| [prototype](prototype/SKILL.md) | Throwaway prototype to flesh out a design before committing to it. |
| [yeet](yeet/SKILL.md) | Stage + commit + push + open PR in one flow. |
| [write-a-skill](write-a-skill/SKILL.md) | Author new skills with proper structure. |
| [capture-source](capture-source/SKILL.md) | Store a web source's content + metadata into the project knowledgebase (deterministic, no model spend) instead of dropping a bare link. |

### Matt Pocock engineering set (v1.1.0)

| Skill | Description |
|-------|-------------|
| [research](research/SKILL.md) | Background agent investigates a question against primary sources into a cited Markdown file. |
| [domain-modeling](domain-modeling/SKILL.md) | Build / sharpen the project's ubiquitous language; record ADRs. |
| [codebase-design](codebase-design/SKILL.md) | Shared vocabulary for designing deep modules and placing seams. |
| [code-review](code-review/SKILL.md) | Two-axis review (Standards + Spec) of a diff or branch. |
| [resolving-merge-conflicts](resolving-merge-conflicts/SKILL.md) | Resolve an in-progress git merge / rebase conflict. |

### Orchestration and role skills

| Skill | Description |
|-------|-------------|
| [orchestration](orchestration/SKILL.md) | Agent roster, situation-to-skill routing, spawn contract, playbooks, pre-ship gate, verdict ledger. |
| [setup-models](setup-models/SKILL.md) | Interview the user role by role, then rewrite the orchestration model map. |
| [code-quality](code-quality/SKILL.md) | Cross-language standard for writing, reviewing, and refactoring code, with per-language references. |
| [architect-designer](architect-designer/SKILL.md) | Settle system structure and author the code skeleton before any logic is written. |
| [art-director](art-director/SKILL.md) | Sub-orchestrator for one image generation or editing workstream. |
| [big-pickle-simple-tasks](big-pickle-simple-tasks/SKILL.md) | Turn paralyzing scope into small sequenced action items. Read-only. |
| [implementation-specialist](implementation-specialist/SKILL.md) | Execute a scoped implementation task with zero architectural drift. |
| [requirements-clarifier](requirements-clarifier/SKILL.md) | Turn a vague task into user stories, acceptance criteria, and edge cases. Read-only. |
| [skeptic-gate](skeptic-gate/SKILL.md) | Independent pre-ship challenge check on a plan or diff. Read-only. |
| [tech-lead](tech-lead/SKILL.md) | Sub-orchestrator for one software workstream, delegating every piece of work. |
| [test-automation-engineer](test-automation-engineer/SKILL.md) | Write and run tests, diagnose failures, verify fixes by execution. |

### Principle skills

| Skill | Description |
|-------|-------------|
| [laziness-protocol](laziness-protocol/SKILL.md) | Deeper subtraction pass when a diff keeps growing layers, wrappers, and options. |
| [never-block-on-the-human](never-block-on-the-human/SKILL.md) | Proceed on reversible work instead of stopping to ask permission. |
| [prove-it-works](prove-it-works/SKILL.md) | Observe the real artifact before declaring anything done. |
| [guard-the-context-window](guard-the-context-window/SKILL.md) | Route bulk output to subagents and keep only summaries in the main thread. |
| [encode-lessons-in-structure](encode-lessons-in-structure/SKILL.md) | Turn a rule that keeps recurring into a mechanism, then delete the prose. |
| [foundational-thinking](foundational-thinking/SKILL.md) | Pick the core data shape and the order of work before writing logic. |
| [outcome-oriented-execution](outcome-oriented-execution/SKILL.md) | Converge on the target architecture instead of shimming every intermediate commit green. |
| [experience-first](experience-first/SKILL.md) | Spend effort where the consumer feels it, and cut surface area to keep the core tight. |
| [exhaust-the-design-space](exhaust-the-design-space/SKILL.md) | Compare two or three competing prototypes side by side before committing. |
| [redesign-from-first-principles](redesign-from-first-principles/SKILL.md) | Rebuild the design as if the new requirement had been known on day one. |

### Prose and session management

| Skill | Description |
|-------|-------------|
| [unslop](unslop/SKILL.md) | Cut AI tells and shape register, format, and length of any writing. |
| [rotate-agent](rotate-agent/SKILL.md) | Rotate a bloated long-running subagent into a fresh one via a transient handoff doc. |
| [impeccable](impeccable/SKILL.md) | Design, critique, and polish frontend interfaces; spawns its own fleet. |
| [teach](teach/SKILL.md) | Embody a domain-expert teacher and build tracked learning material. |
| [excalidraw-diagrams](excalidraw-diagrams/SKILL.md) | House standard for Excalidraw diagrams, including Obsidian-embedded ones. |

### Godot and demo work

| Skill | Description |
|-------|-------------|
| [godot-headless-cli](godot-headless-cli/SKILL.md) | Drive Godot 4.x from the shell without opening the editor. |
| [godot-playtest](godot-playtest/SKILL.md) | Drive a running Godot game through godot-mcp to verify a change in-game. |
| [blender-godot-pipeline](blender-godot-pipeline/SKILL.md) | Retarget external animation onto a Godot character via headless Blender. |
| [demo-video-capture](demo-video-capture/SKILL.md) | Capture the benchmark clip set for a nikki-net demo build. |
| [demo-video-judge](demo-video-judge/SKILL.md) | Judge a captured clip set against the demo GDD gates and file bugs. |
| [demo-friction-log](demo-friction-log/SKILL.md) | Record a framework friction hit from demo development into the GDD. |
| [clip-to-mobile](clip-to-mobile/SKILL.md) | Convert a gameplay clip into a small mobile-viewable video. |

### Tools and integrations

| Skill | Description |
|-------|-------------|
| [agent-workbench](agent-workbench/SKILL.md) | One CLI over the knowledgebase vault, bd board hub, and artifact review service. |
| [comfyui](comfyui/SKILL.md) | Drive a local ComfyUI instance headlessly over its HTTP API. |
| [proton-pass-cli](proton-pass-cli/SKILL.md) | Retrieve credentials from Proton Pass via pass-cli. |
| [azure-devops](azure-devops/SKILL.md) | Read-only queries against Azure DevOps repos, pipelines, and work items. |
| [cloudflare](cloudflare/SKILL.md) | Query Cloudflare zones, DNS exposure, rulesets, WAF posture, and Workers routes. |
| [snyk](snyk/SKILL.md) | Query the Snyk REST API for projects, targets, and issues. |
| [sysdig](sysdig/SKILL.md) | Query Sysdig Secure for runtime vulnerability posture and secure events. |
| [ox-security](ox-security/SKILL.md) | Query OX Security as a connector aggregator for issues, apps, and repo-to-runtime paths. |

### Archived

| Skill | Description |
|-------|-------------|
| [build-software](archived/build-software/SKILL.md) | Superseded phased feature-build pipeline. Kept for reference, not routed to. |
