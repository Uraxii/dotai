### Architect planning

**You own the planning handoff. Obtain the design before the writer changes code.**

1. Use an unclaimed step bead for planning. If the owner holds that step, create an unclaimed `chore` child under it. If the code-writing step has no planning bead, create an unclaimed `chore` child under that step. Keep the owner's claim on the parent. Use [Run records](../../ticket-work/references/run-records.md) for record commands.
2. Read the requirements planner's recorded mode per [Requirements planning](../../run-workflow/workflows/code-change-workflow.md#requirements-planning). For a recorded Lightweight decision that skips architecture, close the planning bead with `skip: Lightweight mode: <reason and scope>`. Otherwise, continue with the design handoff.
3. Otherwise, claim the planning bead under the planner's actor before the spawn. Spawn a fresh agent with the configured architect planning model. Follow [Models](../SKILL.md#models) for overrides and fallback.
4. Give the planner the worktree, scope, constraints, done-when, output paths, and evidence. Request [architect](../../architect/SKILL.md) Phases A through C only. The plan names the caller's usage, types, signatures, modules, and implementation step. The planner implements no production logic.
5. Receive the design and rationale, artifact paths, implementation scope, and unresolved decisions.
6. Close unused Phase D with `skip: implementation belongs to the writer`. Close unused Phase E with `skip: no architecture scrap needed`. Use the planner's actor for these phase commands. If the sketch needs a scrap, use the architect redesign loop. After the applicable checks pass, close the planning bead under the planner's actor.

   ```sh
   BEADS_ACTOR=<planner-actor> bd close <planning> --reason "<handoff result and evidence>"
   ```

   The planner does not close the owner's parent step or an Orchestrate unit.
7. Give the writer the plan and implementation scope. A plan can cover a defined batch of related edits. Do not repeat architect planning for work that the plan covers.
8. A change outside the plan's scope returns to [Requirements planning](../../run-workflow/workflows/code-change-workflow.md#requirements-planning). A new requirement, changed contract, or failed shape stops dependent work until that phase supplies the required context.

An agent without database access follows [Run records](../../ticket-work/references/run-records.md#agents-that-cannot-reach-the-database).
An agent that cannot spawn returns the planning need to its spawner before implementation.
The spawner follows the recorded requirements mode and obtains any required plan.
A writer's private task list does not replace the architect design package.

**Reply:** the design paths, implementation scope, unresolved decisions, and applicable sketch receipts.
