---
id: py.logging.no-print
languages: python
scope: contextual
severity: warn
enabled: true
detectors: ruff:T201
exclude: tests/*, test_*.py, *_test.py, conftest.py, scripts/*
---
Use `logging` instead of `print` in library and app code.
