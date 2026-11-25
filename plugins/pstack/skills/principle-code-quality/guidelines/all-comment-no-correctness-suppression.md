---
id: all.comment.no-correctness-suppression
languages: python, typescript, javascript, csharp, gdscript
scope: global
severity: warn
enabled: true
detectors:
---
Never silence a correctness or safety check (`eslint-disable`, `@ts-ignore`, `@ts-expect-error`, `noqa`). Fix the flagged symbol instead. A style-only suppression such as `prettier-ignore` may stay.
