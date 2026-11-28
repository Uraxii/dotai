---
id: py.function.mutable-default
languages: python
scope: contextual
severity: block
enabled: true
detectors: ruff:B006
---
No mutable default arguments such as `def f(x=[])`. Default to `None` and build the value inside the function.
