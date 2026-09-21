# pstack skill tree source

27 skills in this plugin are a port from `michael-denyer/pstack-claude`, replacing
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
principle-redesign-from-first-principles, reflect, show-me-your-work, swarm,
tdd, teach, technical-writing, unslop, why.

Each was replaced wholesale (directory deleted, then copied from source) using
`.nikki-agents/adopt_pstack_claude.py`. `poteto-mode` was ported in a separate
commit; see that commit's message for what the swap changes.

## Local to this plugin

Every other skill under `plugins/pstack-nikki/skills/` is specific to this
project and was not touched by the port: `caveman`, `create-artifact`,
`decisions`, `handoff`,
`wayfinder`, `podman-sandbox`, `notion-cli`, `principle-code-quality`,
`principle-naming`, `principle-decomposition`, `principle-output-to-user`,
`azure-devops`, `cloudflare`, `codebase-memory`, `domain-modeling`,
`grilling`, `llm-wiki`, `ox-security`, `prototype`, `rotate-agent`,
`setup-dotai`, `skill-quality`, `snyk`, `sysdig`, `README.md`.
