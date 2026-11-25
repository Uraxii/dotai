---
id: ts.typing.construct-legal-values
languages: typescript
scope: global
severity: warn
enabled: true
detectors:
---
Construct types so the illegal value cannot exist. Use `[T, ...T[]]` for non-empty, `[T, T][]` for even length, and `start` + `duration` for a range.
