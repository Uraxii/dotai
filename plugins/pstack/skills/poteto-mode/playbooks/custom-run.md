### Custom run

The owner runs this playbook when no narrower playbook fits.
Use [Run records](../../ticket-work/references/run-records.md) for the run and its step beads.
Use [Models in poteto-mode](../SKILL.md#models) for model selection, overrides, and fallback.

1. Give figure-it-out the scope, done-when, and constraints. Request its framing and workflow design before execution. Ask it to return the proposed workflow at the end of Phase B.
2. Check the workflow against [Production checks](production-checks.md). For production work, insert a sketch review after each architect synthesis and before implementation. Insert a diff review after each writer. For production code, insert the dedicated test gate after the diff pass. Put runtime verification after both current passes.
3. Create the designed step beads under the execution phase. Run the revised workflow with figure-it-out's experiment and audit method. The owner chooses and runs the required gates through Production checks.
4. Check the final artifact against the done-when. Check the gate receipts against the final patch. Report the workflow, evidence, unresolved items, and final SHA.

Keep experiment checks in figure-it-out. Use Production checks for production review order, pass acceptance, and failure limits.
