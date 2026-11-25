---
id: cs.async.no-blocking
languages: csharp
scope: contextual
severity: warn
enabled: true
detectors:
---
Use `async`/`await` for IO. No `.Result`, `.Wait()`, or `.GetAwaiter().GetResult()`.
