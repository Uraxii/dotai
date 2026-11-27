---
id: cs.async.configure-await
languages: csharp
scope: contextual
severity: warn
enabled: true
detectors: roslyn:CA2007
---
Use `ConfigureAwait(false)` in library code. Omit it in app and UI code.
