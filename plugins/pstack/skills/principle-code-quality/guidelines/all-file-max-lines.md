---
id: all.file.max-lines
languages: python, typescript, javascript, csharp, gdscript
scope: contextual
severity: warn
enabled: true
detectors: pylint:C0302, eslint:max-lines, gdlint:max-file-lines
---
Keep each file at 600 lines or fewer, with one cohesive responsibility. Split it by responsibility when it grows past that.
