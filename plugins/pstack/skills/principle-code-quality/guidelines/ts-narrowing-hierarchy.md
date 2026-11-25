---
id: ts.narrowing.hierarchy
languages: typescript
scope: global
severity: warn
enabled: true
detectors:
---
Narrow with discriminated unions, not type casts. Use the best tool that works, in this order: discriminant switch, `in`, `typeof` or `instanceof`, a user-defined type guard, and `as` last.
