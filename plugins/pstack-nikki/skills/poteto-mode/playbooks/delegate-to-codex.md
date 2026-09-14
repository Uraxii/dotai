# Delegate to Codex

Pick when: a `developer-codex` or `reviewer-codex` agent holds a poteto-agent
brief and must run it as a real Codex session on a GPT model, not imitate
GPT locally.

1. Confirm the brief carries every spawn field (`references/brief.md`). A
   brief missing GOAL, SCOPE, ACCEPTANCE, or VERIFY is a refuse-to-spawn
   condition, same as any other spawn.
2. Prepare the worktree yourself; Codex wires no isolation hook.
   - Writer brief (`developer-codex`): `git worktree add
     .nikki-agents/worktrees/<name> -b agent/<name>` before you call Codex.
   - Read-only brief (`reviewer-codex`): no worktree. Point Codex at the
     existing checkout and pass `-s read-only`.
3. Check whether pstack-nikki's poteto-mode is installed in Codex: `codex
   plugin list`. Look for `pstack-nikki` at `installed, enabled`; the
   top-level `dotai` plugin installing does not count, its poteto-mode is a
   different, less-scoped skill. As of 2026-09-14 only `dotai` is installed
   here, so treat pstack-nikki as not installed unless a fresh check says
   otherwise. Either way, the relay script below handles it: it always
   points Codex at the SKILL.md's absolute path rather than naming the
   skill, so a name collision with the other poteto-mode never happens.
4. Run the relay script from your worktree root:

   ```
   python3 plugins/pstack-nikki/skills/poteto-mode/scripts/codex_relay.py \
     --agent developer-codex \
     --brief-file <path-to-brief> \
     --cwd <worktree-path>
   ```

   Swap `--agent reviewer-codex` and drop the worktree for a review brief
   (the script then defaults `-s read-only`). The script reads the codex row
   for that agent from `models.json`, picks its first slug, builds the
   poteto-agent prompt (preamble plus the brief verbatim), and calls `codex
   exec`. Pass `--model <slug>` only to override the row for a deliberate
   reason (state it in your report); a slug outside the row can fail outright
   (a ChatGPT-account login rejects `gpt-5.4-mini` even though it lists in
   `available.codex`, confirmed live 2026-09-14) or run the wrong-tier
   model.
   - Long runs: launch the command via background execution (Bash's
     `run_in_background`, or the harness's equivalent) and wait for the
     completion notification. A GPT-5.5 run against one tiny brief took
     about 75 seconds live 2026-09-14; do not block the turn on it.
5. On success the script prints Codex's final message, the poteto-agent's
   own report, to stdout. Read it like any other subagent report: verify the
   claimed diff and branch yourself (`git -C <path> log`, `git -C <path>
   diff`), never pass it through unverified.
6. On failure the script prints `codex exec`'s stderr tail and exits
   non-zero. One confirmed cause: **wrong model for the account.** Codex
   logged in with a ChatGPT account 400s on some `available.codex` slugs
   (`gpt-5.4-mini`, live 2026-09-14: `The 'gpt-5.4-mini' model is not
   supported when using Codex with a ChatGPT account`). Drop `--model` and
   let the script use the row's first slug, or confirm the slug works for
   this login before pinning it.
   - The suspected risk that a worktree's gitdir
     (`<main-repo>/.git/worktrees/<name>`, outside `-C`) would block
     `git commit` under `workspace-write` did not reproduce live
     2026-09-14: a Codex run committed inside a fresh worktree with no
     `--add-dir` needed. Codex's `workspace-write` sandbox reported writable
     paths as `[workdir, /tmp, $TMPDIR]`; the worktree's `.git` file itself
     lives inside `workdir`, and Codex's git handling reaches the real
     gitdir past that boundary without tripping the sandbox. If a future
     run does hit a sandbox denial on the gitdir, the relay script's
     `--add-dir <main-repo>/.git` flag is there to widen the writable set.
7. Confirm the result the way you confirm any delegate's work
   (`principle-prove-it-works`): read the actual commit or diff before
   reporting it landed, never the agent's self-report alone.

**Reply:** model and sandbox picked, whether the SKILL.md fallback path was
used, the commit or branch you confirmed yourself, or the blocker hit
verbatim.
