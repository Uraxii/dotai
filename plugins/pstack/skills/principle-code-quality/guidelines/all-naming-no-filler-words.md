---
id: all.naming.no-filler-words
languages: python, typescript, javascript, csharp, gdscript
scope: global
severity: warn
enabled: true
detectors: pylint:C0104, eslint:@typescript-eslint/naming-convention, roslyn:IDE1006
---
Name the thing and its effect. Do not use structure filler (Manager, Controller, Handler, Helper, Util, Service, Data, Info, Object, Item) or scheduling words (Deferred, Pending, Delayed, Async, Lazy) as identity.
Service is allowed only under an established subsystem convention, and its prefix must still carry meaning.
