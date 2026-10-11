### Architecture change

The owner runs this playbook for a direct architecture request.
The design agent returns the design. The owner checks the evidence and gives the scope to the writer.
Use [Run records](../../ticket-work/references/run-records.md) for the run and its step beads.
Use [Models in poteto-mode](../SKILL.md#models) for model selection, overrides, and fallback.

1. Give the architect skill the application scope, constraints, and done-when. Request synthesis in Phases A through C. Tell the design agent to return the sketch and rationale before implementation.
2. If the user requests a human checkpoint, present the design and wait for approval. Include this checkpoint in the design brief.
3. For production work, commit the sketch and rationale. Obtain the sketch pass per [Production checks](production-checks.md) before implementation. Record the gate ID and pass SHA.
4. Check the design paths, scope, and unresolved decisions. Give the writer the accepted sketch and request implementation against it.
5. After the writer reports its committed head, obtain the diff pass per [Production checks](production-checks.md). For production code, obtain the dedicated test pass too. Check that both passes cover the final patch, including tester edits.
6. Verify the behavior at runtime after the required current passes. Report the design, the gate evidence, and the final SHA. Run [Opening a PR](opening-a-pr.md) when the brief requires a PR.

For work that has no production gate, record the exclusion under Production checks.
