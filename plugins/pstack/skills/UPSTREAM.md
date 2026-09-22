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
commit; see that commit's message for what the swap changes. The bro and teach
skills were later removed from this plugin, so those two names no longer
resolve to a skill here. Both names stay plain here, never in bold or
backticks, on purpose. `scripts/validate-skills.py` reads an emphasised name
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

## Ported from a gist

- Source: https://gist.github.com/geoffreylitt/a29df1b5f9865506e8952488eac3d524
- Revision: `126e7fe9eecaafadfe1ac8bb183d135812b608f2`
- Skills: explain-diff-html and explain-diff-notion, each a verbatim copy of
  its gist file.

A local skill named create-artifact merged both of them into one. It has been
deleted in favour of the two originals, so that name no longer resolves to a
skill here. No skill name in this section is emphasised, and that is
deliberate. `scripts/validate-skills.py` reads a bolded or backticked name as
a citation of a live skill, and the two gist skills move to a package of
their own, which this tree must not cite.

## Local to this plugin

Every skill directory in this tree that no section above names is local to
this project and came from neither port. Read the directory listing for the
current set. A list written out here would go stale every time a skill
arrives or leaves, and it already did once.
