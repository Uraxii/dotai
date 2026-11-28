---
id: gd.comment.no-body-comments
languages: gdscript
scope: global
severity: warn
enabled: true
detectors:
---
No comments inside function bodies. If a step needs an explanation, rename or split it. A transient `# TODO` stub is the only exception.
Detector, must print nothing: `grep -rnP '^\s+#' src --include='*.gd'`
