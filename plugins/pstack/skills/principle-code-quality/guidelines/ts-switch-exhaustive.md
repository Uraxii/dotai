---
id: ts.switch.exhaustive
languages: typescript
scope: contextual
severity: warn
enabled: true
detectors: eslint:@typescript-eslint/switch-exhaustiveness-check
---
Make every switch exhaustive. Put `const _exhaustive: never = x;` in the default arm, so a new variant breaks the build.
