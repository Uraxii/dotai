---
id: py.error.no-assert-in-prod
languages: python
scope: contextual
severity: warn
enabled: true
detectors:
---
No bare `assert` in production code, because `-O` strips it. Use `raise` instead.
