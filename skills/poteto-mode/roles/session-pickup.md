# Session pickup

Pick when: "take over this", "resume this conversation", "continue from
<transcript path>", "you are taking over", "pick up where X left off", a
handoff document, or a pushed branch you are meant to continue. You own the
resume point. Read the prior trail; do not redo it.

A pickup is inheritance. The prior agent already paid the cost of reading the
code, running the repros, making the design choices. Redoing loses the bias
check and burns context. Resist the urge to re-derive; read.

1. Locate the prior trail: a local transcript under the active workspace's
   transcript directory, a handoff document, or a pushed branch. Do not glob
   across other workspaces; that crosses boundaries and reads private chats
   from unrelated projects. Read the metadata overview and last messages
   first, then scan back for the decision points. Parse a long transcript in a
   subagent and keep the reduced timeline in the main thread
   (`principle-guard-the-context-window`).
2. Reconstruct operational state: the branch and worktree, what already landed
   (`git log`, `git diff` against the base), open todos, decisions made. The
   prior trail is authoritative input. Resist the bias to re-derive it.
3. Diff done vs pending. Compare what shipped against what was planned, name
   the resume point, do not re-run the prior repro or redo completed work. A
   "let me verify from scratch" pass is the tell that you are treating the
   trail as untrustworthy when it is authoritative.
4. Route the remaining work to the matching role and pick the verdict:
   continue the execution, ship a finished recommendation, ratify or override
   a prior conclusion, or postmortem a failed run. This role ends here; the
   routed role owns the rest.
5. Verify the inherited claims against the original goal on the real artifact
   (`principle-prove-it-works`). A passing prior self-report is not the proof.

**Reply:** where the prior agent stopped, what you inherited vs redid (ideally
nothing redone), the resume point, the outcome.
