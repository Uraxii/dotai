---
id: all.error.no-broad-catch
languages: python, typescript, javascript, csharp
scope: contextual
severity: warn
enabled: true
detectors: ruff:BLE001, eslint:no-empty, roslyn:CA1031
---
No catch-all or empty catch blocks. Catch the errors you can handle and handle each one explicitly, per the surrounding context.
