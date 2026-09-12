# GDScript rules

- Type hints: all vars, params, returns. Static typing mode on.
- `@onready` over `_ready()` assignment for node refs.
- Signal connections: prefer `connect()` in code over editor (auditable).
- No `get_node("../../..")` chains. `@export` node paths or use groups.
- `_process` / `_physics_process`: guard w/ early return if inactive.
- Resource preload: `const` + `preload()`, not runtime `load()`.
- State machines: enum + match, not boolean soup.
- `await` for async (Godot 4). No deprecated `yield`.
- Null-check before scene tree access. Freed nodes = crash.
- Signals over direct method calls for decoupled communication.
- `class_name` on reusable scripts. Skip for one-off scene scripts.
- `StringName(&"...")` for frequent lookups (input actions, anims).
- No `get_tree().get_nodes_in_group()` in `_process`. Cache result.
- `@export` over `_ready()` param injection for inspector-configurable values.
- `is_instance_valid()` before accessing refs that may be freed.

## Doc comments (`##`)

- `##` = editor help. `#` = plain. Default: no doc. `##` says WHY only; never restate name, type, params.
- Member doc <= 2 lines, directly above member. Trailing form fine: `var hp: int ## Current health.`
- No file-level `##` header. File purpose = name + `class_name`/`extends`.
- No comments inside function bodies. Step needs explaining -> rename or split. `# TODO` stub only, transient.
- No `##` on `_private` members or lifecycle overrides (`_ready`, `_process`). Unclear private -> rename.
- Never cite ADRs, CLAUDE.md, tickets, commits in `##`. Reader = user of the API.
- BBCode: `[ClassName]` `[method m]` `[member m]` `[signal s]` `[param p]` `[code]x[/code]` `[codeblock lang=gdscript]`.
- Detector, must print nothing: `grep -rnP '^\s+#' src --include='*.gd'`.

## Style

- Null: `if not x` / `if x`. Never `== null`.
- Logic nested in `if` -> guard clause + early return.
- Name by effect, not metaphor: `grant_control` -> `set_owner`; `TIME_EPSILON_SECONDS` -> `REVIVE_TIME_SEC`.
