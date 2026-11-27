# GDScript and Godot guidelines

Generated from `guidelines/` by `scripts/guideline_references.py`.
Edit the guideline files, then run the script.

- `gd.async.await` (warn): Use `await` for async (Godot 4). No deprecated `yield`.
- `gd.class.class-name` (warn): Put `class_name` on reusable scripts. Skip it for one-off scene scripts.
- `gd.comment.no-body-comments` (warn): No comments inside function bodies. If a step needs an explanation, rename or split it. A transient `# TODO` stub is the only exception. Detector, must print nothing: `grep -rnP '^\s+#' src --include='*.gd'`
- `gd.doc.bbcode` (warn): Use BBCode in docs: `[ClassName]` `[method m]` `[member m]` `[signal s]` `[param p]` `[code]x[/code]` `[codeblock lang=gdscript]`.
- `gd.doc.member-length` (warn): Keep a member doc to 2 lines or fewer, directly above the member. The trailing form is fine: `var hp: int ## Current health.`
- `gd.doc.no-file-header` (warn): No file-level `##` header. The file purpose is its name plus `class_name`/`extends`.
- `gd.doc.no-private-docs` (warn): No `##` on `_private` members or lifecycle overrides (`_ready`, `_process`). If a private member is unclear, rename it.
- `gd.doc.no-process-references` (warn): Never cite ADRs, CLAUDE.md, tickets, or commits in `##`. The reader is a user of the API.
- `gd.doc.why-only` (warn): `##` is editor help and `#` is a plain comment. Default: no doc. A `##` doc says WHY only. Never restate the name, type, or params.
- `gd.export.inspector-values` (warn): Use `@export` for inspector-configurable values, not param injection in `_ready()`.
- `gd.group.cache-lookup` (warn): No `get_tree().get_nodes_in_group()` in `_process`. Cache the result.
- `gd.lookup.string-name` (warn): Use `StringName` (`&"..."`) for frequent lookups such as input actions and animations.
- `gd.naming.effect-names` (warn): Name by effect, not metaphor: `grant_control` -> `set_owner`; `TIME_EPSILON_SECONDS` -> `REVIVE_TIME_SEC`.
- `gd.nesting.guard-clause` (warn): When logic is nested in an `if`, use a guard clause and an early return.
- `gd.node.is-instance-valid` (warn): Call `is_instance_valid()` before you access a ref that may be freed.
- `gd.node.no-parent-chains` (warn): No `get_node("../../..")` chains. Use `@export` node paths or groups.
- `gd.node.null-check-before-tree` (warn): Null-check before scene tree access. A freed node causes a crash.
- `gd.node.onready` (warn): Use `@onready` for node refs, not assignment in `_ready()`.
- `gd.null.truthiness` (warn): Check null with `if not x` or `if x`. Never `== null`.
- `gd.process.early-return` (warn): In `_process` and `_physics_process`, guard with an early return when inactive.
- `gd.resource.preload` (warn): Preload resources with `const` + `preload()`, not runtime `load()`.
- `gd.signal.connect-in-code` (warn): Connect signals with `connect()` in code, not in the editor, so the connections can be audited.
- `gd.signal.decouple` (warn): Use signals, not direct method calls, for decoupled communication.
- `gd.state.enum-match` (warn): Write state machines as an enum plus `match`, not as a set of booleans.
- `gd.typing.static-hints` (warn): Put type hints on all vars, params, and returns. Keep static typing mode on.

## All languages

- `all.comment.no-commented-out-code` (warn): Delete commented-out code instead of keeping it as a comment.
- `all.comment.no-correctness-suppression` (warn): Never silence a correctness or safety check (`eslint-disable`, `@ts-ignore`, `@ts-expect-error`, `noqa`). Fix the flagged symbol instead. A style-only suppression such as `prettier-ignore` may stay.
- `all.complexity.cognitive` (warn): Keep cognitive complexity at 15 or less per function. Flatten with guard clauses, or extract a function.
- `all.complexity.cyclomatic` (warn): Keep cyclomatic complexity at 10 or less per function. Replace a long branch chain with a map, registry, or discriminated union, or extract a function.
- `all.file.max-lines` (warn): Keep each file at 600 lines or fewer, with one cohesive responsibility. Split it by responsibility when it grows past that.
- `all.function.max-lines` (warn): Keep each function at 40 lines or fewer. Extract a named function when it grows past that.
- `all.line.max-length` (warn): Keep lines at 80 characters or fewer. Allow up to 100 when the longer line reads better.
- `all.literal.no-magic-numbers` (warn): No magic numbers. Use a named constant that carries the domain and the units, as in `REVIVE_TIME_SEC`.
- `all.naming.no-filler-words` (warn): Name the thing and its effect. Do not use structure filler (Manager, Controller, Handler, Helper, Util, Service, Data, Info, Object, Item) or scheduling words (Deferred, Pending, Delayed, Async, Lazy) as identity. Service is allowed only under an established subsystem convention, and its prefix must still carry meaning.
- `all.nesting.max-depth` (warn): Keep nesting at 3 levels or fewer. Use guard clauses with early returns, or extract a function.
- `all.string.second-language` (warn): No second language in a string past one line, such as SQL in a string, a Python heredoc in shell, or shell in YAML. Give it its own file so its linter checks it.
