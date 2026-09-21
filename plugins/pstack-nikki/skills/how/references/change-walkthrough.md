# Change walkthrough

Use this outline when explaining a code change, diff, branch, or PR. Reuse
the exploration workflow in [../SKILL.md](../SKILL.md).

## Establish the comparison

Identify the requested base and head revisions, or the staged and unstaged
working-tree changes being explained. Record that comparison in the output.
Use the PR's actual base when explaining a PR. Include untracked files only
when they belong to the requested change. Ask when multiple plausible targets
would materially change the explanation.

Read the surrounding code, callers, tests, and configuration needed to explain
both the previous and resulting behavior. Distinguish observed behavior from
inferred motivation, and name any part that could not be verified.

## Teaching outline

1. **Background.** Introduce the existing system and the prerequisites for
   understanding this change. Include a skippable introduction for beginners,
   then narrow the explanation to the affected components. Use a known reader
   profile to avoid repeating material the reader already understands.
2. **Intuition.** Establish the idea behind the change before implementation
   detail. Show small concrete inputs and outputs, comparing old and new
   behavior where helpful. Use figures to make relationships visible.
3. **Code.** Do a high-level walkthrough of the changes to the code. Order
   the walkthrough by execution or dependencies, with prose introducing each
   relevant file. Link code and tests to the behavior they implement.
4. **Quiz.** Write five multiple-choice questions of medium difficulty. Test
   whether the reader understands the change's behavior, edge cases, and
   tradeoffs. Explain why each answer is correct or incorrect. Avoid gotchas.

Keep distractors plausible, options comparable in length, and correct-answer
positions varied. For a rich artifact, let
[create-artifact](../../create-artifact/SKILL.md) present the answers and
feedback in the selected format. A quiz helps find gaps; it does not certify
correctness or block review. Do not answer on the user's behalf or record an
unobserved quiz pass.

Keep the prose clear and engaging, with smooth transitions between sections.
Reuse a small set of diagram styles. Show simplified UI for UI changes, and
example values alongside component or data-flow diagrams. Add callouts for
definitions, key concepts, and important edge cases.

## Source

Adapted from Geoffrey Litt's `explain-diff-html` and `explain-diff-notion`
[skills](https://gist.github.com/geoffreylitt/a29df1b5f9865506e8952488eac3d524).
Their shared teaching sequence is retained here; output rules live in the
HTML and Notion references. Revision scope and quiz checks are dotai additions.
