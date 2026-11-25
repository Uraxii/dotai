---
id: ts.typing.honest-type-guards
languages: typescript
scope: global
severity: warn
enabled: true
detectors:
---
Make each type guard verify the claim it makes. A lying guard is worse than `as`. Name guards `isX` or `hasX`.
