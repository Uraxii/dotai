# Autopilot-full

Pick when: "autopilot this queue", "full autopilot", a one-owner-per-PR
program. The job is a queue of independent PRs handed over to drive to merged
with full autonomy. You own the verdicts, never the PRs. One owner runs each
PR from build to merge, and nothing merges without your clean verdict.

Orchestrate runs a standing program whose coordinator lands verified work
itself and whose workers never merge. Here each PR's owner carries the whole
lifecycle through the merge, and the root keeps verification, countersigns,
and audits.

1. **Mark the user's items and honor state-then-wait.** Items the user names
   stay hers. She reviews and she clicks, and no owner merges one. Asked to
   state the protocol or the plan -> deliver the statement and stop. Execution
   starts only on her explicit go.
2. **Spawn one owner per PR with the full lifecycle.** One `orchestrator`
   subagent per PR owns build, self-proof on the real artifact
   (`principle-prove-it-works`), skeptical triage of review-bot comments, a
   pass of `unslop` over the diff, the comment rule in
   `principle-code-quality`, a rebase onto current trunk, the Babysit loop to
   green (`roles/babysit.md`), and the merge itself. The rebase always
   precedes babysit and never waits for drift or conflicts. Every owner keeps
   a decision trail per `show-me-your-work`, never committed, returned with
   its report. The merge is the one step an owner may not take alone; step 4
   gates it.
3. **Run owners in true parallel and never stack.** Many owners at once when
   PRs are self-contained: one writer per branch, disjoint files, cross-PR
   drift absorbed by rebase. Only genuinely overlapping work serializes.
   Self-contained PRs branch straight off main, and sequenced work is
   merge-then-branch. One exception: an owner that must split a genuinely
   dependent change may hold a short private stack.
4. **Verify every merge-ready head before its merge.** At the owner's
   merge-ready head SHA, fan out parallel independent verifiers per `swarm`
   and aggregate to one verdict. The fan-out mechanics live there; do not
   restate them. The lanes: re-run the gates at that SHA; prove the
   load-bearing behaviour live on the real surface the change touches; audit
   the receipts and the diff, distrusting the PR body. The live lane is the
   floor, and a verdict without it is not clean. No merge without the root's
   clean verdict. Findings go back to the owner for fix-forward, and the new
   head gets a fresh fan-out and a fresh verdict.
5. **On a clean verdict the owner merges and takes the next item.** The owner
   merges only from a head freshly rebased on trunk. The merge-ready report is
   made at a trunk-current head, and the verdict pins that SHA. Trunk moves
   again before the merge -> the patch-id rule in `roles/shipping.md` governs
   re-verification; a new head voids the verdict unless the patch-id is
   unchanged. The owner squash-merges its own PR and picks up its next
   self-contained item from the queue. The user's full-autonomy grant plus the
   root's clean verdict is the merge authorization that babysitting alone never
   has. User-named items stop at merge-ready and wait for her click.
6. **Run the root layer.** A genuinely new raise of a pinned gate or budget
   value (a limit CI only lets tighten) needs your fresh countersign, granted
   only after verifier proof. Absorbing values that already landed on main is
   drift, not a raise. Run an audit tick over all owners roughly every 30
   minutes on a recurring run if the harness has one. Each tick probes
   liveness read-only, audits both progress and protocol adherence, and
   collects the decision trails. When merges batch, run a retro pass and a
   post-merge bot-comment sweep.
7. **Stand down instantly on the user's stop.** Her hold or stand-down reaches
   every owner as a zero-writes order immediately. Owners hold their briefs
   until she releases them.

**Reply:** the queue with each PR's owner, state, and head SHA; each verdict
and the fan-out that produced it; what merged and what each owner took next;
countersigns granted and why; open human gates; where the collected decision
trails live.
