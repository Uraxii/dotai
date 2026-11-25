---
id: ts.typing.brand-primitives
languages: typescript
scope: global
severity: warn
enabled: true
detectors:
---
Brand semantic primitives, as in `type UserId = string & { readonly __brand: "UserId" }`. Validate once at creation and trust the value downstream.
