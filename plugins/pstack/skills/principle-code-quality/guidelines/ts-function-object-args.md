---
id: ts.function.object-args
languages: typescript, javascript
scope: contextual
severity: warn
enabled: true
detectors: eslint:max-params
---
Pass one object argument instead of several positional ones, so each call site names its values.
Skip this on hot paths such as per-frame render code, tokenizers, and parsers.
