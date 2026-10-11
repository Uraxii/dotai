### Architect planning

**You own the planning handoff. Obtain the design before the writer changes code.**

1. Use an unclaimed step bead for planning. If the owner holds that step, create an unclaimed `chore` child under it. If the code-writing step has no planning bead, create an unclaimed `chore` child under that step. Keep the owner's claim on the parent. Use [Run records](../../ticket-work/references/run-records.md) for record commands.
2. For a very small change, record the scope and reason before implementation. Close the planning bead with `skip: very small change: <reason>`. This skip applies only to architect planning. Implementation delegation, tests, diff review, and the tester gate still apply.
3. Otherwise, claim the planning bead under the planner's actor before the spawn. Spawn a fresh agent with the configured architect planning model. Follow [Models](../SKILL.md#models) for overrides and fallback.
4. Give the planner the worktree, scope, constraints, done-when, output paths, and evidence. Request [architect](../../architect/SKILL.md) Phases A through C only. The plan names the caller's usage, types, signatures, modules, and implementation step. The planner implements no production logic.
5. Receive the design and rationale, artifact paths, implementation scope, and unresolved decisions. For production work, commit the synthesized sketch and rationale. Obtain the sketch pass before implementation per [Production checks](../references/production-checks.md). The owner checks the receipts and follows its three-failure stop limit.
6. Close unused Phase D with `skip: implementation belongs to the writer`. Close unused Phase E with `skip: no architecture scrap needed`. Use the planner's actor for these phase commands. If the sketch needs a scrap, use the architect redesign loop. After the applicable checks pass, close the planning bead under the planner's actor.

   ```sh
   BEADS_ACTOR=<planner-actor> bd close <planning> --reason "<handoff result and evidence>"
   ```

   The planner does not close the owner's parent step or an Orchestrate unit.
7. Give the writer the plan and implementation scope. For production work, also give the writer the sketch SHA and passed gate. A plan can cover a defined batch of related edits. Do not repeat architect planning for work that the plan covers.
8. A change outside the plan's scope needs a new plan or the owner's very-small-change skip. A new requirement, changed contract, or failed shape returns to architect planning.

An agent without database access follows [Run records](../../ticket-work/references/run-records.md#agents-that-cannot-reach-the-database).
An agent that cannot spawn returns the planning need to its spawner before implementation.
The spawner obtains the plan or records the owner skip.
A writer's private task list does not replace the architect design package.

**Reply:** the design paths, implementation scope, unresolved decisions, and applicable sketch receipts.
