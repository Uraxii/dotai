# Model map

Per-role model pinned per Agent call via `model` argument. Never frontmatter.

`setup-models` skill rewrites this file. Edit by hand only if that skill is
unavailable; re-running it overwrites the whole table.

Allowed values: `sonnet`, `opus`, `haiku`, `fable`, where `fable`, `sol`,
and `luna` are NEVER assigned without explicit user permission.

| Role skill worker loads | Model |
|---|---|
| architect-designer | opus |
| skeptic-gate | opus |
| tech-lead | opus |
| art-director | sonnet |
| implementation-specialist | sonnet |
| requirements-clarifier | sonnet |
| test-automation-engineer | sonnet |
| big-pickle-simple-tasks | haiku |

Role absent from table -> omit `model`, child inherits parent.

`fable` maps to NOTHING here. Never spawn fable, sol, or luna without
explicit user permission.
