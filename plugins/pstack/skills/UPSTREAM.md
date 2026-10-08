# pstack skill tree source

40 skills in this plugin are a port from `michael-denyer/pstack-claude`, replacing
an earlier, less maintained port of the same Cursor `pstack` origin.

- Source: https://github.com/michael-denyer/pstack-claude
- Revision: `2fe2002190bff9257d3e27f84ba6818f2cfd7e32`
- License: MIT, retained in the upstream repo's `LICENSE` and `NOTICE.md`.

## Ported from pstack-claude

architect, arena, blast-radius, bro, figure-it-out, how, interrogate,
poteto-mode, principle-build-the-lever, principle-encode-lessons-in-structure,
principle-exhaust-the-design-space, principle-experience-first,
principle-foundational-thinking, principle-guard-the-context-window,
principle-laziness-protocol, principle-never-block-on-the-human,
principle-outcome-oriented-execution, principle-prove-it-works,
principle-redesign-from-first-principles, reflect, setup-pstack,
show-me-your-work, swarm, tdd, teach, technical-writing, unslop, why.

Each was replaced wholesale (directory deleted, then copied from source) using
`.nikki-agents/adopt_pstack_claude.py`. `poteto-mode` was ported in a separate
commit; see that commit's message for what the swap changes. The bro, teach,
and show-me-your-work skills were later removed from this plugin, so those
three names no longer resolve to a skill here. All three names stay plain
here, never in bold or backticks, on purpose. `scripts/validate-skills.py` reads an emphasised name
as a citation of a live skill and fails the build.

## Imported later, same revision

The ported `poteto-mode` names these as skills to load, but that script only
replaced directories already present, so none of them came across with it:

deslop, no-comments, principle-attack-the-premise,
principle-boundary-discipline, principle-fix-root-causes,
principle-make-operations-idempotent,
principle-migrate-callers-then-delete-legacy-apis,
principle-minimize-reader-load, principle-model-the-domain,
principle-separate-before-serializing-shared-state,
principle-sequence-verifiable-units, principle-subtract-before-you-add,
principle-test-behavior-not-implementation, principle-type-system-discipline.

Each is a verbatim copy of the source directory at the revision above. Several
overlap in subject with the local `principle-code-quality`, which was left
untouched; consolidating them is a separate decision.

## setup-pstack, and the tooling deliberately left behind

`setup-pstack` was copied from the same revision and then rewritten where
upstream's model schema is flat. Upstream keys a role to one list of Claude
slugs; this plugin keys every role by harness (`claude`, `codex`, `copilot`),
so the ported skill had to say how a per-harness override works. The answer is
that the sheet's path is the harness key: `~/.claude/pstack-models.md`
overrides the `claude` entries, `~/.codex/pstack-models.md` the `codex` ones.
See the skill itself for the rest.

No file from upstream's `tools/` was taken. Upstream's `tools/generate.mjs` is
the stamper for the flat schema, and it also stamps a `VERSION` file,
`CHANGES.md`, `docs/reference.md`, Codex prompt stubs, and a marketplace
manifest that this repo does not have. Nothing stamps model picks here any
more: this repo's own stamper was retired along with the copied-out `##
Models` tables, and `scripts/validate-models.py` keeps only its validation
half. Upstream's `sync.mjs`, `substitutions.json`, `upstream.json`,
`validate-skills.mjs`, and `verify-merge-safety.mjs` serve upstream's own
release pipeline and were not taken either.

## create-artifact, deleted

A local skill named create-artifact merged two skills ported from a gist into
one. It has been deleted in favour of the two originals, which now live in
the artifact and notion plugins with their own upstream-source.md beside each
SKILL.md. The gist source and revision went with them, because both belong to
those skills and not to this tree.

That name no longer resolves to a skill here, so it stays in plain prose.
`scripts/validate-skills.py` reads a bolded or backticked name as a citation
of a live skill and fails the build.

## Delegation, orchestration, and pause/resume run on beads

This tree diverges from upstream here. Delegation, orchestration, and
pause/resume run on beads (bd 1.3.1 with the official `gastownhall/beads`
plugin). The upstream run-dir and store mechanisms are removed:

- A delegated task is a bead. Its scope and acceptance criteria are the bead's
  description and acceptance, and its result is the bead's close reason.
- `create_agent_run.py` and the run directories are deleted. The Codex watchers
  `developer-codex` and `reviewer-codex` take a bead ID.
- The show-me-your-work skill and its decision log are deleted.
- `scripts/orch/` is deleted. The orchestrate playbook keeps its state in
  beads.
- `resume.mjs` is deleted. Pause and resume read and write beads.
- The official beads plugin replaces `plugins/beads`.

The changes landed in pull requests #125 through #131. A skill ported from the
revision above and later changed by those pull requests no longer matches
upstream. Re-syncing one of them from upstream restores the run-dir text.

## Feature and refactoring workers run on Sonnet

This tree diverges from upstream here. The `feature, refactoring` role in
`models.json` lists only `sonnet` for Claude and drops `claude-opus-5` from
Copilot. The `poteto-mode` Agent-call defaults send every code delegate to the
role's first model instead of tiering the hardest changes to the
strongest-judgment model. Re-syncing either file from upstream restores the
tiering.

## Local to this plugin

Every skill directory in this tree is local to this project unless a section
above lists its name among the skills that section took from a source. Those
lists are the enumerations of skill names in each section. A name that a
section mentions only in surrounding prose is not one of them. Read the
directory listing for the current set. A list written out here would go stale
every time a skill arrives or leaves, and it already did once.
