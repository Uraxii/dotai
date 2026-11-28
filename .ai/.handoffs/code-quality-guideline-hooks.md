# Handoff: code-quality guidelines delivered by hooks (pstack `principle-code-quality`)

## Objective

Make the `principle-code-quality` skill guide agents to readable code the way OX VibeSec
guides security: small per-rule guideline files with metadata, delivered by hooks at the
right moment, with lint detectors that inject corrections or block an edit.

Motivating case: an agent that followed the skill wrote
`return tuple(page for path in paths for page in parse_page(_read(path)))`.
ruff (ALL), pylint, mypy --strict, wemake, radon, complexipy and lizard all pass it.

## State of the branch

Everything is on `feature/code-quality-guideline-hooks` (same commits as
`ccr-ed13ddee-s8qbaa`), branched from `develop`. No PR is open. Do not merge yet.

| Piece | Where | State |
|---|---|---|
| Comprehension checker (CQ001 two `for` clauses, CQ002 `f(g(x))` in a comprehension) | `plugins/pstack/skills/principle-code-quality/scripts/code_quality.py` + test | Done, tested |
| Language id -> extensions map (57 languages, GitHub Linguist) | `.../principle-code-quality/languages.toml` | Done |
| 94 guideline files (frontmatter: id, languages, scope, severity, enabled, detectors) | `.../principle-code-quality/guidelines/` | Done; every `detectors:` is blank on purpose |
| Hook core + Claude Code adapter + Codex adapter + `check` CLI | `.../scripts/guideline_*.py`, `plugins/pstack/hooks/guidelines.sh`, `hooks.json`, `codex-hooks.json`, `hooks/tests/guidelines.test.sh` | Built, 85/85 hook tests pass; reviewed, findings open |
| Copilot CLI adapter, Pi adapter | - | Not built (payload formats unverified) |
| SKILL.md and `references/*.md` | unchanged | Still the old prose; needs a hooks section and `metadata.version` bump |

Because all detectors are blank, the hooks deliver guidance text only. Nothing blocks yet.
The deny for the motivating case works once `py-comprehension-one-for.md` has
`detectors: code_quality:CQ001` (proven by piping a payload into the hook).

## Read these (do not re-derive)

- `.ai/guideline-hooks-design.md`: the spec. Hook list, frontmatter keys, runner contract,
  session state, per-harness contract and degradation table, tests, unit plan.
- `.ai/guideline-hooks-review-findings.md`: 12 findings from an independent review, ranked,
  each with a repro and a fix. Verdict: not safe to enable blocking yet.
- `.ai/guideline-hooks-md-changes.md`: proposed `detectors:` values and SKILL.md text.
- `.ai/guideline-mapping.md`: every guideline id with scope, severity and intended detectors.
- `.ai/code-quality-lint-plan.md`: history. Its steps 3-6 are superseded by the "Revised
  design" section at its end.

Scratch paths named in those notes (under `/tmp/...`) are gone; ignore them.

## Decisions that bind the rest of the work

1. A false negative (missed violation) is worse than a false positive. Unsure -> deliver as
   warn. Block only on an unambiguous new detector hit on a `severity: block` guideline.
2. A project's own standards, guidance, configs and lints take precedence over the guideline
   files. Run tools with the project's config; an explicit project ignore turns that rule off.
3. A hook failure never blocks the user's work and is never silent.
4. Detectors are open source CLI tools only (ruff, pylint, mypy, eslint, lizard, complexipy,
   opengrep/semgrep, gdlint, dotnet analyzers, `code_quality.py`). No hosted service, so drop
   the `sonar:` codes in the mapping. Hooks may use what the harness itself provides.
5. No vectors, no customization layer, no TOML of limits. `enabled: false` in a guideline
   file is the only switch. (A plugin update overwrites it; accepted for now.)
6. Guideline data lives in Markdown frontmatter, flat `key: value`, comma lists.
   `languages.toml` is the only TOML.
7. Enforcement hooks go in the plugin's `hooks/*.json`, never in SKILL.md frontmatter
   (skill hooks start only after the skill loads, and are Claude Code only).
8. Must work on every harness dotai ships to: Claude Code, Codex, Copilot CLI, Pi, and
   skills-only harnesses (opencode, Hermes, Gemini CLI, Cursor) through the `check` command.
9. Scope global = sent once when a language is first seen. Contextual = sent when a detector
   or keyword fires. A guideline is global when any language it lists has no detector.
10. Judgement prose (types and boundaries, domain modelling, reader load, sequencing, smells,
    scope) stays in SKILL.md and is not split into guidelines.

## Next steps, in order

1. Fix review findings 1-6 (and 7-12 if cheap), each with a test, then get a fresh
   independent review. Finding 1 is one flag (`--force-exclude`).
2. Fill in `detectors:` in the guideline files from the mapping and the proposed-changes
   note, minus `sonar:`. Each `tool:code` may belong to one guideline only.
3. Add runners for pylint, mypy, lizard, complexipy, gdlint and the C# analyzers, or leave
   those guidelines as warn with the "detector unavailable" notice.
4. Update SKILL.md: point to `guidelines/` and the `check` command, state that project
   standards win, bump `metadata.version`, then run
   `python3 scripts/generate-plugin-manifests.py` and its `--check` (it fails today for the
   version bump only). Decide whether `references/*.md` is deleted or generated from the
   guideline files; today it duplicates them.
5. Build the Copilot CLI and Pi adapters after confirming their payload formats on a real
   session. Confirm on a real Codex that `PostToolUse` fires for `apply_patch`.
6. Measure hook latency. Then open a PR to `develop`.

## Known gaps

- Unverified harness facts are listed at the end of the hook writer's work in the design
  note (`[guess]` labels) and in the review note ("Not checked").
- `cs.typing.no-dynamic` is `block` with no detector; nothing enforces it.
- The repo's own `plugins/asd-ste100/.../ste-lint.py` scores cognitive complexity 348 and
  cyclomatic 312. It will fail any complexity gate. Track separately.
- The hook prefers project-local tools (`.venv/bin/ruff`, `node_modules/.bin/eslint`), so
  editing in an untrusted repo runs that repo's code once detectors are filled in.

## Gotchas in this repo

- A repo hook blocks every Markdown write outside `.ai/` unless the user's latest chat
  message contains the word "markdown". A dialog answer does not count, and a subagent
  cannot receive the permission. Ask the user to type it, then write all Markdown in the
  main session in one turn.
- `AGENTS.md`: before any merge, run Open Code Review (`/open-code-review:delegate-review
  --from <base> --to <head>`) and fix or answer each finding. Reviewers must be fresh agents.
- Features branch off `develop`. `main` only receives merges from `develop`.
- `README.md` in each skill folder is generated; do not edit it by hand.

## Commands

    mise exec -- python3 plugins/pstack/hooks/tests/guidelines.test.py
    mise exec -- bash scripts/run-hook-tests.sh
    (cd plugins/pstack/skills/principle-code-quality/scripts && python3 -m unittest)
    python3 scripts/generate-plugin-manifests.py --check

## Suggested skills

- `pstack:poteto-mode` first, then its Bug fix playbook for the review findings.
- `pstack:principle-code-quality` and `pstack:principle-test-behavior-not-implementation`
  for any code or test change.
- `skills:skill-quality` before editing SKILL.md or the guideline files.
- `open-code-review:delegate-review` before merge.
- `pstack:write-pr` when opening the PR.

## Progress (review-fix loop closed)

- Review-fix chain on `feature/code-quality-guideline-hooks`: 257cab4, d85f6c2, 0f30926, 24fa503, 1fb60e6, 88f65a7, dddb160, b2b38ee (pushed).
- Fresh review of b2b38ee: 0 blocking, 0 non-blocking (`.ai/review/review-b2b38ee.md`).
- Tests on Python 3.12 (mise): guidelines.test.sh 140/140, all hook suites 188/188, unittest 13 OK, ruff clean. System python3 is 3.10 and fails the unit tests.
- User asked: build everything in Python; announce issued guidelines in chat; mise and the Devin blueprint install Python.
- Done: `hooks/guidelines.py` replaces `guidelines.sh` (runs on any Python 3.6+, finds a 3.11+ for the engine, same fail-open log rules); manifests run `python3 .../guidelines.py` (Windows `py -3`). `guidelines.test.py` replaces the shell suite (153 pass). Each context or deny that issues guideline bodies has a line asking the agent to tell the user the IDs (`announcement()` in guideline_core.py; 400 chars reserved from the cap; `check` has none). Merged develop (40fc24a); its `mise.toml` (Python 3.12.12, `mise run ci`) replaces mine; the repo blueprint also installs Python 3.12.
- `mise run ci` fails only at check:manifests: principle-code-quality SKILL.md needs a metadata.version bump (Markdown, waits for approval).
- Next: detectors: values, SKILL.md, references/*.md decision, manifests, PR to develop. All edit Markdown outside `.ai/`, which waits for user approval ("markdown").

## Update: review of a4aaad2 fixed (dfef3e9, ea0c273)
- Manifests chain `python3 -I || python -I || py -3 -I || notice/true`; wrapper has a catch-all (exit 0 + systemMessage) and makes the data dir 0700.
- Announcement follows VibeSec's pattern (user: "Follow VibeSec's pattern."): exact first line `pstack code quality: <ids> guidelines provided`; ANNOUNCE_CHARS 1500, reserved only once a call issues a guideline body.
- guidelines.test.py 160/160; mise run test 171/171. Fresh review of 0bddba1..ea0c273 pending.

## Update: reviews of ea0c273 and 2bd48f3 fixed (2bd48f3, d114d19); Markdown approved (a46313c)
- Announcement names exactly the issued IDs; add() reserves len(announcement(issued + new)). ANNOUNCE_CHARS removed.
- Unix commands: `for python in python3 python3.14..python3.11 python; do "$python" -I guidelines.py <h> 2>/dev/null && exit 0; done; notice|true` (no stdin buffering: `cat` may be off PATH). Codex Windows: `hooks/guidelines.cmd <h> [start]`, untested on Windows.
- Wrapper sets umask 077; Codex gets systemMessage too; notices shrink context cap by 60 so the omitted-count line fits; inconclusive old-file scan gives a notice.
- User said "Yes, markdown.": detectors filled from guideline-mapping.md (no sonar:), cs.async.no-blocking now global, keywords/exclude added, `scripts/guideline_references.py` generates references/*.md (unittest checks), SKILL.md 1.1.0.
- mise run ci green: guidelines.test.py 175/175, hook total 171/171, unittest 15 OK, manifests current.
- Final fresh review of 90b0211..a46313c: session dd9f3aa4b48c4964a57c3f60bd0e76bd. Then PR to develop (do not merge).

## Update: review dd9f3aa4 findings fixed
- Codex `@@ anchor` lines are found before the hunk; `*** End of File` hunks match the last copy; a missing anchor gives the "could not build" notice.
- Finding identity drops trailing comments (`COMMENT_MARKERS`), so a comment-only edit to a violating line is not new.
- Launcher: each candidate first runs a `-I -c` version probe with stdin from /dev/null; only the first that starts gets the payload. Wrapper failure prints a systemMessage; no Python prints a SessionStart notice or a per-call systemMessage. `guidelines.cmd` does the same (untested on Windows).
- `Finding.blocks`: ESLint severity 1 is a warning. Ruff codes in the project's global ignore are not passed to `--extend-select`, so ruff's own config decides (ignore ALL + select F403 reports F403); per-file ignores still drop the detector.
- ESLint ids match exactly (`matches_code`); ruff runs only on Python (`runs_on`); ruff gets `--preview`; only successful tool probes are cached.
- Detector codes: complexipy:CC001, tsc:TS1294, roslyn:CA1502, mypy strict replaced with mypy error codes. SKILL.md says manual `check` needs Python 3.11+.
- mise run ci green: guidelines.test.py 191/191, hook total 171/171, unittest OK, manifests current. The 9 ruff findings in scripts/ predate this branch's last change and are not in CI.

## Update: review 663a734b findings fixed
- Ruff: codes the project selects or ignores anywhere in its `extend` chain are not added to `--extend-select`; ruff decides. A `preview` key anywhere in the chain drops `--preview`.
- Comment identity also drops `/* ... */` spans and text up to a closing `*/` (block comment opened on an earlier line).
- Codex apply: drops the final empty line like Codex, EOF hunks search only at the end, insertion-only hunks append, trailing-empty-context retry, result ends with a newline; Unicode punctuation pass in line matching.
- `guidelines.cmd` uses `call` so .bat/.cmd Python shims return control (untested on Windows).
- No-runner tools carry languages, so a Python edit names no roslyn/gdlint. `ts.enum.no-enum` uses `keywords: enum` instead of tsc:TS1294.
- mise run ci green: guidelines.test.py 199/199, hook total 171/171.

## Update: review 9326c90a findings fixed (0 blocking, 3 non-blocking)
- Ruff: project ignores narrower than an added guideline code (PTH123 under PTH) are passed as `--extend-ignore`, since CLI selection beats config.
- `locate()` uses `shutil.which` over node_modules/.bin, .venv/bin, .venv/Scripts, so Windows finds eslint.cmd / ruff.exe.
- Comment identity cuts `//` before looking for a closing `*/`.
- mise run ci green: guidelines.test.py 201/201.

## Update: review 0353786a findings fixed (3 blocking, 1 non-blocking)
- Comment identity: `code_lines()` lexes the whole file (line/block comments, strings, triple quotes, JS template strings) and Hit.text is the line with comments blanked. Replaces the per-line regex.
- Codex apply: hunks are located in the original lines, then replaced from the end (Codex `compute_replacements` + reverse apply), so an insertion before an EOF hunk lands after the original last line.
- Ruff per-file ignores: the hook no longer reads them; ruff applies them itself even to --extend-select codes (verified with ruff 0.17.6). `project_disables`/`ruff_ignored` removed. Narrower ignores are not put on the CLI when the config re-selects the rule as narrowly.
- ESLint: a package.json with `eslintConfig` counts as a project config.
- mise run ci green: guidelines.test.py 207/207.

## Update: review ef54d4a1 findings fixed (4 blocking, 2 non-blocking)
- New-finding rule changed: a rule (tool, code) denies only when the edit raises its count. Comment edits and changed lines next to an old finding keep the count, so they never deny; PostToolUse still shows them as warnings. Line text only picks which hits to name. The comment lexer is deleted.
- Codex apply: hunks at one offset keep patch order; context lines keep the file's text; split on LF only (mixed endings match via the rstrip pass).
- Root: without CLAUDE_PROJECT_DIR, the nearest ancestor of cwd with `.git`, so a Codex session in `src/` finds the project's ruff.toml.
- ESLint runs in the folder of the nearest config, so ESLint 9 loads a nested package config.
- Ruff: a guideline code is left to ruff when the config names it or any rule under it (no --extend-ignore).
- parse_patch is linear; a 100k-line Add File runs in about 0.1 s.
- mise run ci green: guidelines.test.py 215/215.

## Update: review d4f1136e findings fixed (0 blocking, 3 non-blocking)
- Ruff: `ruff_ignores()` finds the config's last word on a narrower rule (parent configs first; most specific selector wins; ignore wins a tie). Those rules go on the CLI as `--extend-ignore`, so `ignore = ["PTH123"]` keeps PTH118 on. Checked with real ruff.
- Codex apply: `changed_runs()` makes one replacement per `-`/`+` run between context lines, as Codex does, so insertions at one offset keep Codex's order.
- parse_patch splits on `\n` only and drops a trailing `\r`, like Rust `str::lines()`; a form-feed line is context.
- mise run ci green: guidelines.test.py 220/220.

## Update: review 081215ee findings fixed (4 blocking, 2 non-blocking)
- Codex apply matches lines without their CR, as Codex does, so a CRLF line matches before a later LF line; the file's own line endings are kept.
- Patch file headers and markers are read after `strip()`, as Codex trims them.
- A Codex move scans the old text at the source path and the new text at the target path, so per-file ignores count correctly.
- ESLint runs in the nearest flat-config folder; with only legacy configs it runs at the root, where it reads `.eslintignore`.
- Ruff: a rule the config selects again inside an ignored prefix (ignore PTH1, select PTH123) is added to `--extend-select`. Checked with real ruff.
- Tools are found in `node_modules/.bin` and `.venv` of every folder from the file up to the root (nearest first), then PATH; the probe cache is keyed by tool and path.
- mise run ci green: guidelines.test.py 226/226.

## Update: review a807a7fc findings fixed (5 blocking, 2 non-blocking)
- Codex: several sections for one file apply in order; the original text stays the baseline and PostToolUse reads the file once.
- Codex parser: in an update body an indented line is context (a `*** Move to` there is not a move); a move counts only right after its Update header; `@@` anchors and `*** End of File` lose trailing whitespace.
- Codex apply splits source at LF, CRLF and bare CR, matches without terminators, and keeps the file's terminators.
- Ruff: a config that sets `select` resets the selectors and ignores of the configs it extends (`ruff_live_tables`). Checked with real ruff.
- ESLint: mode and folder are chosen together. Nearest flat config folder in flat mode; with only legacy configs, or `ESLINT_USE_FLAT_CONFIG=false`, the root in legacy mode (`ESLINT_USE_FLAT_CONFIG=false` set for the run).
- Tool input and output use UTF-8 whatever the locale.
- mise run ci green: guidelines.test.py 237/237.

## Update: review fbb36125 findings fixed (4 blocking, 2 non-blocking)
- An edit that also changes a lint setting file (ruff/pyproject/eslint configs, package.json, .eslintignore, .editorconfig) does not deny; its findings are warnings with a notice, and PostToolUse checks the written result.
- Tools get the source as UTF-8 bytes (no Windows text-mode newline changes); output is decoded as UTF-8.
- Ruff: a `[lint]` setting replaces the same deprecated top-level setting in one config.
- code_quality accepts a leading UTF-8 BOM.
- Codex apply: new lines take the file's first line ending, as in Codex.
- A path Ruff excludes counts as checked with zero findings (notice kept), so a move out of an excluded folder can deny. Checked with real ruff.
- mise run ci green: guidelines.test.py 243/243.

## Update: review a19d0778 findings fixed (0 blocking, 3 non-blocking)
- The same-edit lint-setting check (`setting_applies`) now counts only settings that can change the code file's result: a Ruff config in its folder or above, a file in its Ruff `extend` chain, `.editorconfig` when no Ruff config; an ESLint config, `.eslintignore` or `package.json` with `eslintConfig` in its folder or above, or any script module below its flat ESLint config (it may be imported).
- Deleted files and move sources count. A `package.json` dependency edit no longer lowers a deny.
- Checked with real ruff and ESLint 9. mise run ci green: guidelines.test.py 246/246.

## Update: review e18da9a8 findings fixed (3 blocking, 3 non-blocking)
- `setting_tools` returns the detectors a same-edit setting change can affect; only those tools' findings become warnings (a Ruff config edit keeps a code_quality deny).
- Ruff: a config counts when it is in the chain, or a Ruff config at the current one or closer that Ruff would use (a lower-precedence name in the same folder and a pyproject.toml without `[tool.ruff]` do not). `extend` expands `~` and environment variables, as Ruff does.
- ESLint: `.eslintignore` and legacy names count only outside flat mode. Files a config loads count: quoted relative paths followed through those files, and workspace packages it names that resolve through node_modules into the project.
- Codex: sections apply in order, so a Delete after an Update leaves the file deleted (no deny on the intermediate text).
- Checked with real ruff and ESLint 9. mise run ci green: guidelines.test.py 254/254.

## Update: review 17278fcb findings fixed (4 blocking, 4 non-blocking)
- ESLint: scoped shorthand (`@acme` -> `@acme/eslint-config`, `@acme/x` -> `@acme/eslint-config-x`); a folder import follows its package.json `main`/`exports`; workspace packages are followed through their entry points; legacy configs list only `.eslintrc*`/package.json; with `ESLINT_USE_FLAT_CONFIG=false` a flat config is not a setting; legacy mode counts only the root `.eslintignore`.
- Ruff: a pyproject.toml the edit writes counts only when its new text has `[tool.ruff]`.
- Codex: sections are keyed by normalized path (`./a.py` = `a.py`); a delete keeps the path a moved file came from.
- Files past the 50-file limit still count as settings (`Event.unchecked`).
- Checked with real ruff and ESLint 9. mise run ci green: guidelines.test.py 263/263.

## Update: review db1e2bbe findings fixed (7 blocking, 1 non-blocking)
- ESLint settings no longer copy Node/ESLint resolution. `eslint_loaded` runs `eslint --print-config` once per config with NODE_OPTIONS `--require scripts/eslint_loaded.cjs`; a `node:module` registerHooks resolve hook lists every file Node resolves. A changed file counts if ESLint read it, or it is the nearest package.json of such a file. Covers shorthand, `exports` subpaths and conditions, YAML configs, folder `main`. If the list is unknown (Node without registerHooks, timeout, no eslint), any changed script/JSON/YAML/.eslintignore counts (warn).
- A flat config outranked in ESLint's folder (order js, mjs, cjs, ts, mts, cts) is not a setting. A file can be its own config.
- Settings are scanned only when a deny is possible: 50 files + 20 imported modules now take 2.7 s (was 28 s).
- Ruff `extend` follows the path through symlinks, as Ruff does. Codex: a path a move chain leaves empty gets a delete entry.
- Real ESLint 9 / Node 24 / ruff repros for all 8. The self-config case is checked only with real ESLint (the stub returns the same findings before and after). mise run ci green.

## Update: review eebc8fdc findings fixed (3 blocking, 1 non-blocking)
- `eslint_loaded` finds a project-local eslint (it passed a folder to `locate`, which starts at the parent).
- NODE_OPTIONS gets the recorder path with forward slashes, JSON-quoted (Node reads `\` in quotes as an escape, which broke Windows paths).
- eslint_loaded.cjs also records files read with fs (`readFile*`, `open*`, sync and promises): jiti TypeScript configs and JSON/ignore files a config reads.
- When the loaded list is unknown, the code file itself is not a setting, so a one-file edit still denies.
- Real ESLint 9.39 / Node 24 / jiti repros: local-only eslint denies, a module of eslint.config.ts and an fs-read rules.json lower to warnings.

## Update: review db26c41c findings fixed (4 blocking, 1 non-blocking)
- `eslint_loaded` traces with the ESLint that lints the code file (`locate` from the code file), so a package-local ESLint under a root config traces.
- eslint_loaded.cjs records absent paths the config looks for (and `exists`/`stat`/`access` calls), so adding an optional file the config reads lowers the deny.
- A package.json the edit adds above a loaded file counts (it becomes that file's manifest, e.g. its `imports`).
- Codex sections are keyed by absolute path (`a.py` = `$PWD/a.py`).
- NODE_OPTIONS keeps non-ASCII recorder paths (`ensure_ascii=False`).
- Real ESLint 9 / jiti / ruff repros for all 5. mise run ci green: guidelines.test.py 272/272.

## Update: review c7991908 (cc12e67) - 9 blocking
- Design change: an ESLint deny becomes a warning when the edit changes any data or ignore file (`.json/.jsonc/.json5/.yaml/.yml`, `.*ignore`; not package.json). A package.json counts when it is a loaded file's nearest manifest, or is above a loaded file and is added or names `exports`/`imports`/`main`. Recorder also records failed relative resolves and callback `fs.access/stat/exists/lstat`.
- Codex: sections keyed by realpath (symlink alias = target); a move into a deleted path makes it live again.
- Known limits (for the PR): a symlinked Python file is linted by Ruff with its target folder's settings; a ~1M-line Codex patch can pass the 10 s hook timeout with no notice.
- Real ESLint 9 repros: move into deleted path denies, failed require.resolve / outer exports manifest warn, symlink alias update allows. mise run ci green: guidelines.test.py 275/275.

## Update: review 1a459d58 (bac3150) findings fixed (4 blocking)
- eslint_loaded.cjs records every candidate of a relative lookup (base, base+ext, base/package.json, base/index.*), on success and failure, so a new `rules.js` that shadows `rules/index.js` lowers the deny.
- Codex: deleting a symlink keys by the link, not its target; a path a move left empty starts empty for a later Add; `find_lines` normalizes the file once per pass and checks the first line first (12000-line unanchored hunk: 0.11 s, was > 10 s).
- Real ESLint 9 / ruff repros for all 4. Test added for the large hunk.

## Update: review 6642d619 (6c07e8e) findings fixed (2 blocking, 1 non-blocking)
- The code file is never its own ESLint setting unless its name is a config name: in legacy mode the trace probe is the code file, so every legacy deny became a warning.
- A flat config name outranked in its folder is not a setting, even though ESLint looks for all six names.
- ESLint traces stop at detector deadline + 4 s (`TRACE_GRACE_S`); past it the list is unknown (warn), so the hook stays inside 10 s.
- Real ESLint 9 legacy and flat repros. Tests for the first two.

## Update: review 84581975 (7a94e91) findings fixed (4 blocking, 1 non-blocking)
- Codex: a path whose symlink the patch deleted is keyed by its own path, and a later Add there starts empty.
- eslint_loaded.cjs appends to the list (Node subprocesses of the config record too) and keeps an absent path below the real path of its nearest existing folder.
- The unknown-trace fallback counts `.jsx/.tsx/.jsonc/.json5` too.
- `find_lines` normalizes the file once per form for all hunks and finds the first line with `list.index` (3500 hunks: under 3 s, was 18.7 s).
- Real ESLint 9 / ruff repros for 1, 2, 4; tests for 3 and 5.

## Update: review d3f1e057 (e31bd21) findings fixed (2 blocking, 2 non-blocking)
- eslint_loaded.cjs records lookup candidates only for lookups from project code (not inside node_modules), and also for absolute and `file:` specifiers. typescript-eslint + sonarjs + import-x + stylistic trace: 0.9 s, 2597 lines (was 3.6 s, 44537 lines); the 2-file TS edit denies again.
- Folders project code lists (`readdir`/`opendir`) are kept as `folder/*`; a file the edit adds there counts.
- When the trace gives no list, a notice says the files ESLint reads could not be listed.
- Real ESLint 9 repros for all 4. Do not run `mise -C <repo> exec -- npm`: `-C` changes the cwd to the repo.

## Update: review 3af236a8 (334cad8) findings fixed (0 blocking, 2 non-blocking)
- Every `readdir`/`opendir` is recorded (glob libraries in node_modules list for the config); a file anywhere below a listed folder counts (recursive listings, new subfolders).
- Real ESLint 9 + tinyglobby repro (new subfolder warns, control denies). mise run ci green: 286/286.
