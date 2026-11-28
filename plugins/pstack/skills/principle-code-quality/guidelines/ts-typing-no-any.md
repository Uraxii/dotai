---
id: ts.typing.no-any
languages: typescript
scope: contextual
severity: warn
enabled: true
detectors: eslint:@typescript-eslint/no-explicit-any
---
No `any` without a comment that justifies it (bare external data or generic constraints). Prefer `unknown` and validate at the boundary.
