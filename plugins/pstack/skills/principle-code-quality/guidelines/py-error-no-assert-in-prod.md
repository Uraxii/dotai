---
id: py.error.no-assert-in-prod
languages: python
scope: contextual
severity: warn
enabled: true
detectors: ruff:S101
exclude: tests/*, test_*.py, *_test.py, conftest.py
---
No bare `assert` in production code, because `-O` strips it. Use `raise` instead.
