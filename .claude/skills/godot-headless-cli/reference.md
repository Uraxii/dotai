# Godot headless CLI reference

## Binary discovery

The Godot 4.x binary is managed by the "Godots" flatpak. Versions live under a
per-version dir; do not hardcode one. Discover the newest:

```bash
GODOT=$(ls -1 \
  ~/.var/app/io.github.MakovWait.Godots/data/godot/app_userdata/Godots/versions/*/Godot_v*_linux*.x86_64 \
  2>/dev/null | sort -V | tail -n1)
"$GODOT" --version
```

Override order in `run_headless.sh`: `--godot <path>` > `$GODOT_BIN` (if
executable) > `$GODOT_GLOB` > the built-in `DEFAULT_GLOB` const. Edit
`DEFAULT_GLOB` at the top of the script for a non-flatpak install.

## CLI flag table

| Flag | Meaning |
|------|---------|
| `--headless` | no window, dummy audio + dummy rasterizer. Safe in a shell. |
| `--path <dir>` | project dir (folder with `project.godot`). |
| `-s res://x.gd` / `--script` | run a script. `SceneTree` w/ `--headless`; `EditorScript` needs `--editor`. |
| `-e` / `--editor` | open/attach the editor. Detach from agent shells (see below). |
| `--import` | (re)import assets, then continue/exit. |
| `--quit` | quit after one iteration (pairs with `--editor` for an import pass). |
| `--export-release "<preset>" <out>` | export using a preset from `export_presets.cfg`. |
| `--export-debug "<preset>" <out>` | debug export. |
| `--` | everything after is forwarded to the running script (`OS.get_cmdline_user_args()`). |
| `--version` / `--verbose` / `-q` | version / verbose logs / quiet. |

## SceneTree script pattern

```gdscript
extends SceneTree
func _init() -> void:
    # work here; args after `--` via OS.get_cmdline_user_args()
    quit(0)   # MUST quit or the process hangs. Non-zero = failure.
```

Run: `godot --headless --path <proj> -s res://tools/do_thing.gd -- arg1 arg2`.
`-s` also accepts an ABSOLUTE filesystem path, so a script that lives OUTSIDE
the project `res://` tree (e.g. a bundled skill script) runs without copying it
in: `-s /abs/path/inspect_resource.gd -- <target>`. Args after Godot's own `--`
arrive via `OS.get_cmdline_user_args()`.
`_init()` runs immediately; there is no scene, no rendering. Contrast with an
`EditorScript` (`extends EditorScript`, `_run()`), which needs `--editor` and
full editor context (used by blender-godot-pipeline's `extract_tracks.gd`).

## Runtime GLB/GLTF load (no import pipeline)

The key headless trick for reading external models/anims without the editor or
the import cache:

```gdscript
var doc := GLTFDocument.new()
var state := GLTFState.new()
if doc.append_from_file(path, state) == OK:
    var scene := doc.generate_scene(state)  # a Node tree, AnimationPlayer included
```

Works on any `.glb`/`.gltf` path, inside or outside `res://`. Avoids the
`--import` step and the `.godot/imported` cache-race. `inspect_resource.gd` uses
this for `.glb`/`.gltf` and the normal `ResourceLoader` for `.tscn`/`.tres`.

## Importing assets

`godot --headless --path <proj> --import` (re)imports without opening the
editor. Fallback if a build misbehaves: `godot --editor --path <proj> --quit`
does one editor import pass then exits. Needed when code loads `.import`ed
assets; NOT needed if you read GLBs via the runtime GLTFDocument path.

## Save / convert resources

Inside a `SceneTree` script:

```gdscript
var res := load("res://a.tres")            # or build one in code
var err := ResourceSaver.save(res, "res://out.tres")
# or .res (binary), or drive GLTFDocument.write_to_filesystem() for glb export
```

## GUT tests from CLI

GUT's CLI entry is a `SceneTree` script at `res://addons/gut/gut_cmdln.gd`.

```bash
godot --headless --path <proj> -s res://addons/gut/gut_cmdln.gd \
  -gdir=res://test -gexit
```

| GUT arg | Meaning |
|---------|---------|
| `-gdir=res://test` | directory scanned for test scripts. |
| `-gtest=res://test/x.gd` | run a single test script. |
| `-gprefix=test_` | test file prefix (default `test_`). |
| `-gsuffix=.gd` | test file suffix. |
| `-gexit` | exit process when the run finishes (wrapper adds it if missing). |
| `-gexit_on_success` | exit 0 only when all tests pass. |
| `-gconfig=res://.gutconfig.json` | load options from a config file. |

`scripts/gut_run.sh --project <proj> -gdir=res://test` wraps this, ensures
`-gexit`, and reports PASS/FAIL by exit code. Non-zero exit = failures or load
errors.

## Exporting builds

```bash
godot --headless --path <proj> --export-release "Linux/X11" build/game.x86_64
```

Requires a valid `export_presets.cfg` with a preset of that exact name, and the
matching export templates installed for the engine version. `--export-debug`
for debug builds. Export is out of scope for deep coverage here; verify the
preset name with the editor's Export dialog first.

## Editor from an agent shell

`--headless` runs fine in-shell. Opening the EDITOR (`-e`) from an agent shell
gets SIGKILLed when the turn ends unless detached:

```bash
setsid nohup "$GODOT" -e --path <proj> >/tmp/godot.log 2>&1 &
```

Prefer godot-mcp for live editor control when it is available.

## Gotchas

| Symptom | Reality / action |
|---------|------------------|
| `Pages in use ...`, `RID allocations were leaked at exit` | harmless dummy-renderer shutdown noise. NOT a failure. `run_headless.sh` filters it. Check the exit code. |
| `Leaked instance`, `ObjectDB instances leaked at exit`, `Leaked instance dependency` | same benign headless shutdown noise. |
| Process hangs forever | a `SceneTree` script never called `quit()`. Always quit. |
| Stale / half-imported assets, import hangs | concurrent CLI `--import` racing an OPEN editor's `.godot/imported` cache. Close the editor, or use the GLTFDocument runtime path. |
| Blank output, no rendering | expected: `--headless` uses a dummy rasterizer. |
| Wrong Godot version picked | discovery took the newest by `sort -V`. Pin with `--godot` or `$GODOT_BIN`. |

Noise filter regex used by `run_headless.sh` (extend as needed):
`Pages in use|RID allocations .* leaked at exit|Leaked instance|ObjectDB instances leaked at exit|resources still in use at exit|were leaked`.
Real errors (script errors, missing files, failed loads) are NOT matched and
pass through. The exit code is always the source of truth.

## Cross-reference

Blender retargeting, GLB authoring, and the `extract_tracks.gd` EditorScript
(standalone `.tres` extraction) belong to the
[blender-godot-pipeline](../blender-godot-pipeline/SKILL.md) skill. This skill
covers driving the Godot engine itself from the CLI.
