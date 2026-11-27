---
id: py.typing.strict
languages: python
scope: contextual
severity: warn
enabled: true
detectors: mypy:no-untyped-def, mypy:no-untyped-call, mypy:no-any-return, mypy:type-arg
---
Type-hint every function signature, with `-> None` explicit. No untyped public API.
