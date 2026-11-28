---
id: cs.async.no-blocking
languages: csharp
scope: global
severity: warn
enabled: true
detectors:
---
Use `async`/`await` for IO. No `.Result`, `.Wait()`, or `.GetAwaiter().GetResult()`.
