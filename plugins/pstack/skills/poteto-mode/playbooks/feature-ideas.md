### Feature ideas

You own the proposals. Produce an idea brief and stop before implementation.

Use the [beads work loop](../references/beads-work-loop.md) to create the run bead and five ordered chore step beads before work. Close completed steps with evidence. Record an unavailable step with its reason. Close the idea run after the brief. A future build does not hold it open.

1. Ground the project. Read current design documents, implementation, prior decisions, prior idea briefs, and relevant open beads. Inspect the user workflow when available. Record each access gap. Use the project's code index when available, per [index-the-codebase](../../index-the-codebase/SKILL.md).
2. Give one fresh `poteto-agent` subagent the grounded context and the user's constraints, using your configured judgment and prose model. See [Models in poteto-mode](../SKILL.md#models) for overrides and fallback. Ask it to read `poteto-mode` and [principle-feature-ideas](../../principle-feature-ideas/SKILL.md). Its brief permits read-only inspection and forbids implementation design, task planning, and implementation. If spawning is unavailable or forbidden, produce the same brief yourself. State that limitation.
3. Check each candidate against code, documentation, and active beads. Search synonyms and user-facing names as well as the proposed title. Cite the evidence for each check. State its result as existing, in progress, absent, or unverified. Remove existing and in-progress duplicates. For an extension of an existing feature, state the specific missing behavior. Mark inaccessible evidence as unverified. An access gap does not prove absence.
4. Write the brief in the format below. Preserve ambitious directions that have clear user value. Apply [unslop](../../unslop/SKILL.md). Write `throughput checkpoint: n/a, read-only feature ideas` in the run bead's design field.
5. Present the brief and stop. Ask which idea, if any, to pursue when further work needs that choice. Selection alone does not authorize implementation. On a later selection plus a build request, route to [Feature](feature.md). Route an explicit prototype request to [Prototype](prototype.md). Route an explicit multi-phase planning request to [Multi-phase plan](multi-phase-plan.md) after its design requirements are met.

Do not automatically run `architect`, a review panel, a prototype, production tests, or Opening a PR during an idea run. A request that already specifies behavior to build routes directly to Feature.

#### Brief format

Start with a short project summary. Group proposals under Small improvements, Medium features, and Ambitious directions. These scales describe outcomes. They do not promise effort, priority, dependency order, or delivery dates.

Use these fields for each proposal:

| Field | Content |
|---|---|
| Title | A name that identifies the proposed user behavior. |
| User and need | The person who benefits and the problem or opportunity. |
| Proposed experience | What the user can do or observe. |
| User value | Why that experience helps. |
| Current evidence | The current behavior and its source location. |
| Existence check | The searches or observations and their result. |
| Assumptions | Unknown feasibility or unavailable evidence, stated plainly. |

Do not force a fixed number of ideas. If a scale has no useful proposal, state why. Include no architecture, file-change plan, estimates, dependencies, or task sequence. An idea can name user-visible behavior without specifying its implementation.

**Reply:** the brief, evidence gaps, and any selection needed for further work. Name the run bead. Promise no implementation or delivery.
