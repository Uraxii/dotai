---
id: all.function.max-lines
languages: python, typescript, javascript, csharp, gdscript
scope: contextual
severity: warn
enabled: true
detectors: lizard:length, ruff:PLR0915, eslint:max-lines-per-function
exclude: tests/*, test_*.py, *_test.py, conftest.py
---
Keep each function at 40 lines or fewer. Extract a named function when it grows past that.
