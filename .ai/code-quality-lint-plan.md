# Plan: make principle-code-quality measurable

## Problem

An agent followed the skill and wrote this Python function:

    return tuple(page for path in paths for page in parse_page(_read(path)))

The function is correct but hard to read. At default settings, ruff (ALL,
preview), pylint (all), mypy --strict, wemake, radon, complexipy, and lizard
pass it. Two independent research passes measured this.

Cause: the rule "Comprehensions <=1 nested" has two meanings. Two `for`
clauses can count as one level of nesting. The agent obeyed the rule as
written.

General cause: the skill states measurable limits as prose. Prose has no
check. An agent can read prose in a way that the author did not intend.

## Goal

1. Each rule that a tool can measure names its tool and rule code.
2. The agent runs the tool. The tool output is the verdict, not the prose.
3. The skill measures complexity.
4. The skill keeps prose only for rules that need judgement.

Done means:
- The image function fails a check that the skill tells the agent to run.
- The explicit-loop version of the same function passes that check.
- All rule codes in the skill are verified against upstream docs or a tool
  run.
- `scripts/generate-plugin-manifests.py --check` passes.
- An independent review with no open findings.

## Decision for the user (blocks step 4)

The skill loads in other repositories. Those repositories may have no linter
config. The skill also says "No dependency added without explicit approval."
Choose one:

- A. Recommended. The skill tells the agent to run the repository's own
  linters first. If a repository has none, the agent runs the bundled
  stdlib-only checker plus `uvx`/`npx` one-off runs of the named tools. The
  agent proposes a config to the user. It does not add the config itself.
- B. The skill tells the agent to add the linter config to each repository.
  This conflicts with the dependency rule.
- C. Prose only. The skill names rule codes but does not tell the agent to
  run tools. This is the smallest change. It does not stop the failure.

## Steps

Each step ends in a state that can be checked. Do the steps in this order.

1. Branch. Create the work branch from `develop`. There is no local
   `develop` branch now, so fetch it first. Push only to
   `ccr-ed13ddee-s8qbaa`.

2. Verify the unverified codes. Run each tool or read its docs. Remove a
   code if it cannot be verified. Codes to check:
   - pylint C0302 `max-module-lines`
   - Sonar S103, S3776 (C#)
   - pyright `reportMatchNotExhaustive`
   - tsconfig `erasableSyntaxOnly`
   - `import-x/no-default-export`
   - StyleCop SA1401
   - The cyclomatic limit of 10 (McCabe or NIST 500-235 source)

   Check: each code in the final table has a "verified" mark.

3. Add the comprehension checker (test first).
   - New file: `scripts/check_comprehensions.py`. Use Python stdlib `ast`
     only. Do not add a dependency.
   - Rule CQ001: a comprehension with 2 or more `for` clauses.
   - Rule CQ002: a call in the arguments of a call, inside a comprehension.
     Limit CQ002 to comprehensions only. Across the whole file it gave 369
     hits on this repository.
   - Add a self-test with two fixtures. The image function must fail. The
     loop version must pass.
   - Measure the noise on the repository's Python files. Report the hit
     count.

   Check: the self-test passes, and the noise count is in the PR.

4. Restructure SKILL.md "Hard limits". Use the option the user chose above.
   - Split the section into two parts. "Measured limits" is a table with the
     columns rule, limit, Python, TypeScript, C#, GDScript. "Judgement
     rules" stays as prose.
   - Add one sentence. Run the tools in the table. A clean tool run is
     required. Reading the prose is not enough.
   - Keep "Repo's own documented standard override this file."
   - Do not repeat a rule that has a code. The code is the rule.

5. Add a "Complexity" section to SKILL.md with three limits.
   - Cognitive complexity <=15. Tools: complexipy, sonarjs
     `cognitive-complexity`, S3776.
   - Cyclomatic complexity <=10. Tools: ruff C901, sonarjs
     `cyclomatic-complexity`, S1541, lizard `-C 10`.
   - Nesting <=3. Tools: ruff PLR1702 `max-nested-blocks=3`, sonarjs
     `nested-control-flow`, S134, lizard `-ENS`.
   - Name lizard as the one tool that works on all four languages.
   - Do not set a WPS221 line-complexity limit. One file is not enough
     data. Write this down as an open item.

6. Update the language references.
   - `python.md`: Replace "Comprehensions ≤1 nested" with "One `for` per
     comprehension. No `f(g(x))` inside a comprehension." Add the ruff code
     to each rule (PTH, B006, SIM115, UP031/UP032, F403, T201, S101,
     UP035, I001, PT009/PT027). Add a ready-to-paste `[tool.ruff]` block.
     Add a note: if wemake is used, turn off WPS410, because it forbids the
     `__all__` that this file requires.
   - `typescript.md`: Add the rule names and an ESLint flat-config block.
     Use `@stylistic/max-len`, because core `max-len` is deprecated.
   - `csharp.md`: Add CA, IDE, and Sonar codes and an `.editorconfig`
     block.
   - `gdscript.md`: Add a `gdlintrc` block (`max-line-length`,
     `max-file-lines`). Add lizard for length, complexity, and nesting,
     because gdlint has no rule for them. Keep the existing grep detector.

   Check: each config block runs clean on a clean sample file and fails on
   a bad sample file.

7. Metadata.
   - Bump `metadata.version` in SKILL.md. Versions are checked against
     `main`.
   - Run `scripts/generate-plugin-manifests.py`, then run it again with
     `--check`. Do not edit README.md by hand. The script generates it.
   - Validate per the skill-authoring playbook: frontmatter, referenced
     files exist, links resolve.

8. Eval. Give the old skill and the new skill to fresh agents with the same
   task: write the image function's job ("read and parse every saved page,
   in order"). Compare the outputs. Run the checker on both.

9. Review and PR. Run Open Code Review with `delegate-review`. Fix each
   correct finding. Run the review again until no findings stay open. Open
   the PR to `develop`.

## Out of scope (track separately)

- The ASD-STE100 linter script in this repository fails the new limits
  badly. It has cognitive complexity 348 and cyclomatic complexity 312.
  Open an issue. Do not fix it in this PR.
- TypeScript and C# versions of the comprehension check (`flatMap`,
  `SelectMany`). Nobody has written or tested these yet.
- CI that runs these linters on this repository.

## Rules that stay as prose

Compute or mutate, never both. YAGNI. Illegal states unrepresentable,
branded primitives, parse at the boundary. Domain modelling, deep modules.
Reader load and the 30-second test. Which comments survive, except the
mechanical bans. Subtract first. Idempotency, unowned values. Sequencing,
scope. Feature Envy, Shotgun Surgery, Refused Bequest. Naming by effect.
Only the filler-word ban is mechanical (pylint C0104 `bad-names-rgxs`).

## Evidence

- My research scripts:
  `/tmp/claude-0/-home-user/aab73ae1-b63f-5a04-86e4-83943880a6e2/scratchpad/lint/`
- The second agent's ast-grep rules and runs: `/tmp/claude-0/cq-lint/`
- Both directories are temporary. Copy the fixtures into the PR in step 3.

## Revised design (supersedes steps 3-6): guideline delivery like VibeSec

Customization and TOML dropped. Data lives in Markdown guideline files.

- One file per guideline, flat: `guidelines/<slug>.md` (a guideline can cover several languages).
- Frontmatter, flat `key: value` lines only (stdlib parse, no YAML dependency):
  - `id` unique, e.g. `py.comprehension.one-for`
  - `languages` comma list of ids from `languages.toml`, e.g. `python` or `typescript, javascript`
  - `scope` `global` | `contextual`
  - `severity` `block` | `warn`
  - `enabled` `true` | `false` (user disables a guideline here)
  - `detectors` comma list of `tool:code`, e.g. `ruff:ANN201, ruff:ANN202`
- Body = the guidance text the hook sends.

`languages.toml` (skill root) maps a language id to file extensions. The hook
reads it with `tomllib` to know a file's language:

    [python]
    extensions = [".py", ".pyi"]

    [typescript]
    extensions = [".ts", ".tsx", ".mts", ".cts"]

    [javascript]
    extensions = [".js", ".jsx", ".mjs", ".cjs"]

    [csharp]
    extensions = [".cs"]

    [gdscript]
    extensions = [".gd"]

Test adds: each `languages` entry exists in `languages.toml`; no extension maps to two languages.

Delivery:
1. First Read/Edit/Write of a language's file: send all enabled `global` guidelines for it, once per session.
2. PostToolUse Edit/Write: run the language's detectors on the file; map each finding (tool:code) to its guideline; send body + path:line.
3. PreToolUse Edit/Write: a `block` guideline fires on the post-edit file -> deny with the body as the fix.
4. Skip ids sent in the last N prompts.

Index (tool:code -> id) is built from the frontmatter at run time; never hand-kept.
Test: unique ids; each tool:code maps to one guideline; contextual has >=1 detector;
each tool has a runner; frontmatter keys and values valid.

Open: the plugin cache replaces files on update, so an `enabled: false` edit is lost on update.
