---
id: all.complexity.cyclomatic
languages: python, typescript, javascript, csharp, gdscript
scope: contextual
severity: warn
enabled: true
detectors: ruff:C901, lizard:ccn, eslint:sonarjs/cyclomatic-complexity, roslyn:CA1505
---
Keep cyclomatic complexity at 10 or less per function. Replace a long branch chain with a map, registry, or discriminated union, or extract a function.
