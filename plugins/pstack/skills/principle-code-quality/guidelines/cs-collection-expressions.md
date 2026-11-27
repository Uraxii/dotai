---
id: cs.collection.expressions
languages: csharp
scope: contextual
severity: warn
enabled: true
detectors: roslyn:IDE0028, roslyn:IDE0300
---
Use collection expressions (`[1, 2, 3]`), not `new List<int>{...}` (C# 12+).
