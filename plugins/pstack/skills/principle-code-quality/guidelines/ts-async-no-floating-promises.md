---
id: ts.async.no-floating-promises
languages: typescript
scope: contextual
severity: warn
enabled: true
detectors: eslint:@typescript-eslint/no-floating-promises, eslint:@typescript-eslint/no-misused-promises
---
No floating promises. Await or return each promise, or attach a handler, so every rejection is handled.
