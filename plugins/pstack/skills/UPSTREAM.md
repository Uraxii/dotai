# pstack skill tree source

28 skills in this plugin are a port from `michael-denyer/pstack-claude`, replacing
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
commit; see that commit's message for what the swap changes.

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
manifest that this repo does not have. This repo's
`skills/setup-dotai/scripts/generate-models.py` already stamps the per-harness
schema and stays the only owner of the stamped `## Models` blocks. Upstream's
`sync.mjs`, `substitutions.json`, `upstream.json`, `validate-skills.mjs`, and
`verify-merge-safety.mjs` serve upstream's own release pipeline and were not
taken either.

## Local to this plugin

Every other skill under `plugins/pstack/skills/` is specific to this
project and was not touched by the port: `caveman`, `create-artifact`,
`decisions`, `handoff`, `wayfinder`, `podman-sandbox`, `notion-cli`, `principle-code-quality`,
`principle-naming`, `principle-decomposition`, `principle-output-to-user`,
`azure-devops`, `cloudflare`, `codebase-memory`, `domain-modeling`,
`grilling`, `llm-wiki`, `ox-security`, `prototype`, `rotate-agent`,
`setup-dotai`, `skill-quality`, `snyk`, `sysdig`, `README.md`.
