# Eval

Pick when: testing how a change affects agent behaviour before promoting it. A
new skill variant, a structural change, a prompt tweak. You own the experiment
design. Plan, blind, run, synthesize.

The failure mode is the observer effect. An agent that knows it is being
evaluated behaves differently, so candidates must run blind.

**Non-negotiables for blinding:**

- No `eval`, `test`, `judge`, `experiment`, `rubric`, `score`, `compare`,
  `benchmark`, `candidate`, or `arena` in any directory, file, or prompt the
  candidate sees.
- The candidate prompt looks like an organic user request. State the goal, not
  the meta. "Build me a small todo cli", not "show me how you follow the
  principles chain".
- No chain-eliciting cues. Do not ask the candidate to list which skills,
  principles, or files it applied; that meta-prompt inflates citation
  behaviour. Ask for design notes generally and grade chain-following from
  code shape, not self-report.
- Sanitize directory and slug names. Project-shaped names a user might pick,
  not labels like `candidate-1` or `agent-a`.
- Do not tell the candidate other candidates exist.
- The judge may know it is judging but sees outputs by sanitized label only,
  never by model name.
- Comparing two variants: one judge scores both sets in a single pass on one
  scale, blind to which set each came from. Two judge runs with different
  prompts do not compare; the calibration drifts.

1. **Frame.** State what variant is under test and what behaviour counts as
   success. Write the rubric (3 to 6 concrete criteria) for the judge only.
   Hold it back from candidates.
2. **Set up sanitized environments.** Per-candidate working dir with the
   variant in place. Plant any context an organic task would have: a project
   skeleton, the skills the candidate would naturally read.
3. **Author one organic prompt.** What a user would type. No leakage of what
   is being measured.
4. **Spawn N parallel candidates** on different models per `arena` Phase B.
   Each works in its own sanitized dir; same prompt to each.
5. **Spawn one blinded judge** on a different model family per `arena` Phase
   C. The judge sees outputs by sanitized label and the rubric, never a model
   name.
6. **Verify the chain from transcripts, not self-report.** Read each
   candidate's local transcript under the active workspace's transcript
   directory. Do not glob across other workspaces; that crosses boundaries and
   reads private chats from unrelated projects. Look at which files each
   candidate actually opened. Citing a principle is not reading its leaf
   skill, and reading it is not applying it. Grade chain-following from the
   files it really read plus the shape of the code, never from the candidate's
   own claims.
7. **Read every candidate output yourself** end to end. Compare to the judge's
   verdict. Disagreement means a model is biased or the rubric is ambiguous.
   Synthesize.

**Reply:** variant under test, rubric, per-candidate notes, judge's verdict,
your synthesis, a recommendation on whether to promote the variant.
