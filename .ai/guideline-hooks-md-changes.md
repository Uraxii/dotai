# Proposed Markdown changes for the guideline hooks

The hook implementation did not edit any Markdown outside `.ai/`. These
changes belong to the owner of the skill and the guideline files.

## 1. `plugins/pstack/skills/principle-code-quality/SKILL.md`

Add this section (spec H, unit 11). The `check` command exists and is tested.

```markdown
## Harnesses without guideline hooks

Claude Code and Codex run the guideline hooks for you. If your harness ran no
guideline hook this session, run
`python3 <skill dir>/scripts/guideline_hook.py check <files you changed>`
from the project root after each edit. Fix every `block` line before you
continue, and follow the printed guidelines. The project's own standards,
configs and lints override these guidelines.
```

Also bump `metadata.version` in the same file. `python3
scripts/generate-plugin-manifests.py --check` fails today with "changed since
origin/main but metadata.version is still 1.0.0; bump it". That failure was
there before the hook work.

## 2. `plugins/pstack/skills/principle-code-quality/guidelines/*.md`

Every file has a blank `detectors:` line today, so no detector runs and
nothing can block. Until the lines are filled, the hooks deliver every
guideline of a language as a warning on the first touch of that language.

`python3 plugins/pstack/skills/principle-code-quality/scripts/guideline_lint.py`
lists what is missing: 47 files with "contextual guideline has no detector
and no keyword", and 5 of them also with "block guideline has no detector".

Fill `detectors:` from `.ai/guideline-mapping.md`, with these rules:

- Drop every `sonar:` entry. The linter rejects a tool with no runner entry.
- Write each entry as `tool:code`, comma separated. Known tools: `ruff`,
  `eslint`, `code_quality`, `mypy`, `pylint`, `lizard`, `complexipy`,
  `opengrep`, `semgrep`, `gdlint`, `roslyn`, `stylecop`, `godot`, `tsc`.
  Only `code_quality`, `ruff` and `eslint` run today. The others give a
  notice and deliver the guideline as a warning.
- A `tool:code` pair may appear in one file only.

The two files the motivating case needs:

```
py-comprehension-one-for.md         detectors: code_quality:CQ001
                                    keywords: list comprehension, flatten
py-comprehension-no-nested-call.md  detectors: code_quality:CQ002
```

The linter also asks that the body of `py.comprehension.one-for` names `for`
and `loop`. The current body does.

Optional keys the hooks now read (spec B): `keywords`, `paths`, `exclude`.
Suggested `exclude: tests/*, test_*.py, *_test.py, conftest.py` on
`py.error.no-assert-in-prod`, `all.literal.no-magic-numbers`,
`all.function.max-lines`, and `py.logging.no-print` (plus `scripts/*`).

## 3. `.ai/guideline-hooks-design.md`

Changes the implementation made to the spec, for the spec owner to fold in:

- Every context text and deny reason has a second line, "Project standards,
  configs and lints override these defaults." Tests 1, 2, 3 and 18 change.
- A project tool config wins. With a ruff config (`ruff.toml`, `.ruff.toml`,
  `pyproject.toml` with `[tool.ruff]`) ruff runs without `--isolated` and
  without `--line-length`. A rule in `ignore`, `extend-ignore` or a matching
  `per-file-ignores` entry turns its guideline off for that file: no
  finding, no block, no delivery. Without a ruff config, `.editorconfig`
  `max_line_length` replaces the default 80.
- ESLint runs only with a project config and gets no `--rule` flags. Without
  one the notice reason is `has no project config`.
- The core is three files, not one: `guideline_core.py`, `guideline_files.py`
  and `guideline_runners.py`. One file would pass the 600-line limit.
- New neutral event kinds `cleared` and `check`, and a `channel` field
  (false when the harness cannot take context at that event).
- No `scans` cache in state. A deny keeps undelivered globals in `pending`.
- A file outside the project root gets no output.
- Not built: Copilot CLI adapter, Pi adapter, Stop hook.
