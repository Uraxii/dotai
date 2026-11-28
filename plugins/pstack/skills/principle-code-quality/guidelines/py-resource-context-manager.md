---
id: py.resource.context-manager
languages: python
scope: contextual
severity: warn
enabled: true
detectors: ruff:SIM115, pylint:R1732
---
Open every resource (files, locks, connections) in a `with` context manager.
