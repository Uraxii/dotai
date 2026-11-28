---
id: cs.perf.span
languages: csharp
scope: contextual
severity: warn
enabled: true
detectors: roslyn:CA1846
---
Use `Span<T>` or `Memory<T>`, not array slicing, on perf-critical paths.
