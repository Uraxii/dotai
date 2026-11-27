---
id: all.literal.no-magic-numbers
languages: python, typescript, javascript, csharp, gdscript
scope: global
severity: warn
enabled: true
detectors: ruff:PLR2004, eslint:@typescript-eslint/no-magic-numbers
exclude: tests/*, test_*.py, *_test.py, conftest.py
---
No magic numbers. Use a named constant that carries the domain and the units, as in `REVIVE_TIME_SEC`.
