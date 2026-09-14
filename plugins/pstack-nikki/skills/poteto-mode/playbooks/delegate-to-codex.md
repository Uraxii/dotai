# Delegate to Codex

Claude Code only. Running in any other harness, Codex included: do not use this playbook; do the work yourself.

Pick when: a `developer-codex` or `reviewer-codex` agent holds a poteto-agent
brief and must run it as a real Codex session on a GPT model, not imitate
GPT locally. On Claude Code these two are the default picks for an
implementation unit and a single review gate (SKILL.md, Agents). You are a
worker: the brief's OWNER line holds, and Codex inherits it.

1. Confirm the brief carries every spawn field (`references/brief.md`). A
   brief missing GOAL, SCOPE, ACCEPTANCE, or VERIFY is a refuse-to-spawn
   condition, same as any other spawn.
   Then check Codex can run: `codex --version` and `codex login status` both
   exit 0. Either fails, or the run in step 5 exits non-zero or writes no
   report -> fall back. Prepare the step 2 worktree if you have not, then do
   the brief yourself in it on Claude as a plain `developer` or `reviewer`
   would, and open your report with `fallback: claude` plus the failing
   command's output verbatim.
2. Prepare the worktree yourself; Codex wires no isolation hook.
   - Writer brief (`developer-codex`): one worktree serves both the Codex
     run and any fallback. Spawned with `isolation: "worktree"`, you already
     sit in it (`git rev-parse --git-dir` differs from
     `git rev-parse --git-common-dir`); use it as `-C`. Otherwise run `git
     worktree add .nikki-agents/worktrees/<name> -b agent/<name>` before
     you call Codex or fall back, so neither writes in the main checkout.
   - Read-only brief (`reviewer-codex`): no worktree. Point Codex at the
     existing checkout and pass `-s read-only`.
3. Resolve the poteto-mode skill path yourself. `developer-codex` uses the
   `feature, refactoring` row of `plugins/pstack-nikki/models.json`;
   `reviewer-codex` uses the `judgment and prose` row. Codex may not have
   pstack-nikki's poteto-mode installed (check with `codex plugin list`; as
   of 2026-09-14 only the top-level `dotai` plugin is installed here, and
   its poteto-mode is a different, less-scoped skill), so point the prompt
   at the SKILL.md's absolute path rather than the skill name. From this
   playbook file's own absolute path, poteto-mode's `SKILL.md` sits at
   `../SKILL.md`; resolve that relative path to an absolute one before
   building the prompt, so a name collision with the other poteto-mode
   never happens.
4. Build the prompt: the poteto-agent preamble, a blank line, then the
   brief verbatim. Write it to a file first, the prompt routinely runs
   longer than a comfortable command line.

   ```
   You are operating as poteto-mode's full agent style. Read the
   poteto-mode skill at <absolute path to poteto-mode/SKILL.md> in full
   before doing any work, including its inline Principles index. Navigate
   to a leaf `principle-*` skill whenever you apply that principle.

   <brief verbatim>
   ```

   Save that as, for example, `brief-with-preamble.txt`.
5. Run `codex exec` directly, no relay script in between. Pick the model
   from this file's Models block below: the row's first Codex model, unless
   you have a stated reason to override (state it in your report). A slug
   outside the row can run the wrong-tier model, or fail outright: a
   ChatGPT-account login has rejected some `available.codex` slugs before
   (confirmed live 2026-09-14 with `gpt-5.4-mini`, since dropped from the
   catalog: `The 'gpt-5.4-mini' model is not supported when using Codex with
   a ChatGPT account`), so confirm an override slug works for this login
   before pinning it.

   Writer (`developer-codex`):
   ```
   codex exec -m <first Codex model from the "feature, refactoring" row> \
     -s workspace-write -C <step 2 worktree path> \
     -o <report-file> "$(cat brief-with-preamble.txt)"
   ```

   Reviewer (`reviewer-codex`):
   ```
   codex exec -m <first Codex model from the "judgment and prose" row> \
     -s read-only -C <checkout-path> \
     -o <report-file> "$(cat brief-with-preamble.txt)"
   ```

   A brief too long for `$(cat ...)`'s command-line expansion can go
   through stdin instead: `codex exec -m <model> -s <sandbox> -C <path>
   -o <report-file> - < brief-with-preamble.txt` (codex exec's `PROMPT`
   argument reads stdin when given `-`, confirmed via `codex exec --help`,
   2026-09-14).

   Reasoning effort stays at the account default (medium, set in
   `~/.codex/config.toml`) unless the run needs a push: add `-c
   model_reasoning_effort=low` for a simple lookup, `-c
   model_reasoning_effort=high` for a genuinely hard run.

   Long runs: launch via background execution (Bash's `run_in_background`,
   or the harness's equivalent) and wait for the completion notification.
   A tiny brief ran about 75 seconds live 2026-09-14; do not block the turn
   on it.
6. On completion, read the report file the `-o` flag wrote, Codex's final
   message, same as any other subagent report. Verify the claimed diff and
   branch yourself (`git -C <path> log`, `git -C <path> diff`), never pass
   it through unverified.
7. The suspected risk that a worktree's gitdir (`<main-repo>/.git/worktrees/
   <name>`, outside `-C`) would block `git commit` under `workspace-write`
   did not reproduce live 2026-09-14: a Codex run committed inside a fresh
   worktree with no `--add-dir` needed. Codex's `workspace-write` sandbox
   reported writable paths as `[workdir, /tmp, $TMPDIR]`; the worktree's
   `.git` file itself lives inside `workdir`, and Codex's git handling
   reaches the real gitdir past that boundary without tripping the sandbox.
   If a future run does hit a sandbox denial on the gitdir, `codex exec`'s
   own `--add-dir <main-repo>/.git` flag widens the writable set.
8. Confirm the result the way you confirm any delegate's work
   (`principle-prove-it-works`): read the actual commit or diff before
   reporting it landed, never the agent's self-report alone.

**Reply:** model and sandbox picked, or `fallback: claude` with the failing
output, whether the SKILL.md fallback path was used, the commit or branch you
confirmed yourself, or the blocker hit verbatim.

<!-- dotai:models:start -->
## Models

Stamped from `plugins/pstack-nikki/models.json` (edit there, rerun `generate-models.py`). Row absent -> omit `model`, child inherits. A spawner reads the entry for its own harness.

- `feature, refactoring`: On Claude Code: `sonnet`, `opus`. On Codex: `gpt-5.6-terra`, `gpt-5.6-sol`. On Copilot CLI: `claude-sonnet-5`, `gpt-5.5`, `gpt-5.4`, `claude-opus-5`.
- `judgment and prose`: On Claude Code: `opus`, `sonnet`. On Codex: `gpt-5.6-sol`, `gpt-5.6-terra`. On Copilot CLI: `claude-opus-5`, `gpt-5.5`, `claude-sonnet-5`, `gpt-5.4`.
<!-- dotai:models:end -->
