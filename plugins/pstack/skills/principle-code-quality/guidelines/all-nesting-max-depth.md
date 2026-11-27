---
id: all.nesting.max-depth
languages: python, typescript, javascript, csharp, gdscript
scope: contextual
severity: warn
enabled: true
detectors: ruff:PLR1702, eslint:sonarjs/nested-control-flow, lizard:nested_structures
---
Keep nesting at 3 levels or fewer. Use guard clauses with early returns, or extract a function.
