# Root cause, for a single occurrence

Escalation method. Load when question asks why something happened, once. Runs
inside step 7 per-option analysis, not beside it. Record that it ran and which
trigger fired.

Build explicit causal chain. Identify immediate cause, then keep asking why
that cause existed, working backward until you reach a cause with implications
beyond this one occurrence. Do not stop at first or most obvious.

Frame problem as the unwanted condition or action itself, never as the system
that detected it. "The alert did not fire" is a finding about monitoring, not
the problem.

Never let bare human-error label or bare physical condition stand as stopping
point. Keep asking why until you reach management, design, or training
explanation.

Select exactly one direct cause, exactly one root cause, up to three
contributing causes. Describe each specifically to this occurrence rather than
repeating a category label. Naming one root cause is not the single-cause
fallacy: label is earned only after contributing causes were searched for and
each accepted cause was corroborated.

Require at least two independent pieces of corroborating evidence per accepted
cause in the chain. Where only one exists, document alternative causes you
considered and basis for accepting or rejecting each.

Complete one worksheet per cause: mark it direct, contributing, or root,
describe how it relates to the occurrence, pair it with its own corrective
action. Every identified cause gets a corrective action, not only the root one.
Word each action so somebody else can verify it independently, and name the
specific cause it addresses.

## Pick technique by job

- **Causal factor analysis.** Long chains with several facets.
- **Change analysis.** Cause is obscure. Pick comparable case that did not
  fail, list every difference between the two regardless of apparent relevance,
  then examine each difference for a role in the failure.
- **Barrier analysis.** Physical or procedural barrier failed. Determine
  whether it worked as designed, whether it was maintained and inspected, why
  the unwanted energy was present, whether it could be evaded, whether the
  failure was foreseeable. Then check whether identical barriers elsewhere
  share the flaw.
- **Programmatic review.** Recurring or systemic problems. Name the specific
  control that was less than adequate, then name which management element,
  policy, planning, resource allocation, or verification, let that failure
  happen. Do not stop at the control.
- **Human performance evaluation.** Personnel implicated. Evaluate across
  detection, understanding, action selection, and execution against a
  documented failure-mode list. "Personnel error" alone is not a finding.

Task performed by people under investigation: reenact it step by step with the
person who performs it, observer checking against written procedure and
recording discrepancies. Reconstructing from memory or documents alone misses
the deviation that caused the event.

Occurrence recurs: do not open fresh investigation. Reopen original finding,
determine why its corrective action failed, analyze new occurrence against the
previously fixed case.
