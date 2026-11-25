---
id: ts.typing.strengthen-where-partial
languages: typescript
scope: global
severity: warn
enabled: true
detectors:
---
Keep `T[]` while every operation stays total. Strengthen to `NonEmpty<T>` only where the loose type forces `!`, a cast, or a never-happens throw.
