# Autopilot-stack

Pick when: "autopilot-stack", "stack them, do not ship", "build the stack, I
will land it". You own the stack, never the landing. Build and verify the
queue with full autonomy, then hand the user one linear stack she reviews and
lands herself.

The sibling of Autopilot-full (`roles/autopilot-full.md`). The owner loop and
the verification gate are the same; only the terminal differs. There a clean
verdict authorizes the owner's merge. Here it appends a link to the one
reviewed chain, and nothing auto-ships.

1. **Run the owner loop unchanged.** One `orchestrator` subagent per PR owns
   its change end to end: build, registration of its own PR with the stacking
   tool, self-proof (gates, CI, receipts), skeptical triage of review-bot
   comments, a pass of `unslop` over the diff, the comment rule in
   `principle-code-quality`, and Babysit to green (`roles/babysit.md`). Owners
   parallelize when the work is self-contained. Every owner keeps a decision
   trail per `show-me-your-work`, never committed, returned in its report.
2. **Audit on a wake chain.** The root runs audit ticks roughly every 30
   minutes on a recurring run if the harness has one: liveness per owner,
   progress, protocol adherence.
3. **Hold the user's gates.** State-then-wait, so a request to state the plan
   is not a go. On her stop, every owner takes an immediate zero-writes hold.
4. **Verify at STACK-READY.** The owner reports STACK-READY with the exact
   head SHA. The root fans out verifiers over that SHA per `swarm`: parallel
   independent verifiers re-running the gates at that SHA, a live runtime
   floor over the load-bearing behaviour, and a receipts-and-diff audit that
   distrusts the PR body. They aggregate to one verdict. Findings go back to
   the owner, and nothing enters the stack unverified.
5. **Append on a clean verdict, never ship.** No owner merges, arms
   merge-when-ready, or closes. A clean verdict appends the PR to the one
   linear stack, in verified order or an order the user specified.
6. **Single writer on topology, parallel writers on builds.** Stack mechanics
   follow whatever stacking tool the team uses. An owner pushes only its own
   branch, `git push --force-with-lease` after an `ls-remote` check, and
   reports its tip and intended parent. The root owns stack topology and
   registers each append itself, submitting from the tip. A stack submit walks
   from trunk, and an owner must never pull branches below its own into that
   walk; when instructed, it may set its bottom PR's base directly instead.
7. **Absorb drift at the root, then re-verify what moved.** The root absorbs
   trunk movement by restacking the chain; when a restack surfaces conflicts
   in an owner's files, that owner fixes its own slice and the root pushes the
   result. A restack rewrites every SHA above it and voids the verdicts at the
   old SHAs. Compare `git patch-id` at each verdict SHA against the new head.
   Anything that actually drifted goes back through step 4 before delivery.
   The countersign rule is unchanged from Autopilot-full: a genuinely new pin
   raises a stop for the root's fresh countersign, and absorbing drift of
   landed values is not a raise.
8. **Deliver the chain.** The deliverable is one linear chain of verified PRs,
   reviewable bottom-up, every link carrying its verifier verdict in the PR
   body or a comment. The user reviews and lands it, with her own clicks or
   with merge-when-ready she arms herself.

**Choosing between the autopilots.** Autopilot-full when the PRs are
independent and landing authority is granted. Autopilot-stack when the user
wants review before landing, the work is sequenced or coupled, or merge
authority is withheld.

**Reply:** links to the stack root and tip, a one-line verdict summary per
link, and anything parked or excluded with the reason.
