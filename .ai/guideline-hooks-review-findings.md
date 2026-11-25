# Independent review of guideline hooks (branch ccr-ed13ddee-s8qbaa vs origin/develop)

Verdict: NOT safe to enable blocking by default yet. Today all real guidelines have blank
`detectors:`, so the gate never runs and the hooks only deliver text. Fix 1-4 and the
no-notice part of 6 before filling in detectors. Tests at review time: 85/85 hook tests,
188/188 run-hook-tests, 13/13 unittest.

1. HIGH guideline_runners.py:183-186. ruff run lacks `--force-exclude`, so files the
   project's ruff `exclude` covers get blocked. Repro: pyproject `[tool.ruff] exclude=["migrations"]`,
   Write migrations/m1.py `from os import *` -> deny. Fix: add --force-exclude in both arg branches + test.
2. MED-HIGH guideline_core.py:308 + guideline_runners.py:130. One ignored ruff code drops the whole
   guideline (other detectors, keyword/global delivery, body), no notice. Repro: ignore=["F403"],
   Write `return [g(h(x)) for x in xs]` -> empty output; without the ignore -> deny CQ002.
   Fix: filter per detector; drop the guideline only when all its detectors are disabled, and still send body as warn.
3. MED guideline_core.py:32,293. `build`, `dist`, `vendor` excluded at any depth, silently
   (src/app/build/x.py gets no gate; `check build/b.py` exits 0). Fix: exclude only at root or use
   `git check-ignore`; keep node_modules/.git/.venv/__pycache__ at any depth.
4. MED guideline_core.py:469-475 + suppressed(). Detector failure is silent after the first time
   (notice deduped per session; "detector unavailable" body suppressed 20 prompts). Fix: every call
   where a detector did not run emits at least a one-line item; dedupe only the long text.
5. MED guideline_hook.py:303-307. `check` reports missing / outside-root / excluded paths as clean,
   exit 0. Fix: one notice per unchecked path; non-zero exit for a missing path.
6. MED guideline_hook.py:67-77,80-92,203-217. Post-edit text build fails silently: CRLF files
   (read_text normalises), Codex applier matches context exactly (Codex tolerates trailing whitespace),
   files >1 MB or non-UTF-8 skip checks. Fix: read with newline="", try both line endings, trim
   fallbacks like Codex's applier, and emit a notice when the text cannot be built.
7. LOW hooks/guidelines.sh:54-55. Fallback error log in shared /tmp can be redirected via planted
   dir/symlink when CLAUDE_PLUGIN_DATA and PLUGIN_DATA are unset. Fix: write only in a dir we own
   (`[ -O ]`), refuse symlinks (`[ -L "$log" ]`).
8. LOW hooks/codex-hooks.json commandWindows bypasses the wrapper (no log, no systemMessage; usage
   errors exit 2 = block on Codex). guideline_hook.py:297 show_notice only for claude, so Codex users
   never see notices. Fix: .ps1/.cmd wrapper with same fail-open-and-notify; never exit 2 from main.
9. LOW guideline_core.py:58. Prompt path regex keeps trailing punctuation ("edit main.py." -> no
   language); extensionless shebang scripts never checked; `.h` maps to C. Fix: strip trailing `.`/`,`;
   read shebang for extensionless files.
10. LOW guideline_core.py:461-467 add_hits. Findings over the 9000-char cap dropped with no note.
    Fix: append "N more findings in <file>; run check".
11. LOW coverage: ts-async-no-floating-promises and ts-default-nullish-coalescing are typescript only
    but apply to javascript; all-function-return-types covers only python, typescript.
12. LOW hooks/tests/guidelines.test.sh:296. Wall-clock `SECONDS <= 3` budget test is flaky under load.

By-design risk: the hook prefers project-local tools (.venv/bin/ruff, node_modules/.bin/eslint),
so editing in an untrusted repo runs that repo's code once detectors are filled in.

Checked and fine: session/agent id sanitising; Codex Add File path escapes ignored; upper-case and
two-dot extensions; move+update gated on target path; no shell with payload data (argv lists);
state files atomic, 0600, no prompt text; no double wiring.

Not checked: real Codex/Copilot/Windows runtime; Claude Edit quote normalisation; state-file races.
