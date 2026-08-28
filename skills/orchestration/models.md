# Model map

Per-role model pinned per spawn call via its `model` argument. Never frontmatter.

`setup-models` skill rewrites this file. Edit by hand only if that skill is
unavailable; re-running it overwrites the whole table.

Allowed values: `sonnet`, `opus`, `haiku`. `fable`, `sol`, and `luna` are NEVER
assigned without explicit user permission.

| Role skill subagent loads | Model |
|---|---|
| architect-designer | opus |
| skeptic-gate | opus |
| tech-lead | opus |
| art-director | sonnet |
| requirements-clarifier | sonnet |
| test-automation-engineer | sonnet |
| big-pickle-simple-tasks | haiku |
| interrogate reviewers (list, one subagent each) | opus, sonnet |

Role absent from table -> omit `model`, child inherits parent.
