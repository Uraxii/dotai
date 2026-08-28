---
name: godot-headless-cli
description: Drive the Godot 4.x engine from the command line headless, without opening the editor. Run one-off SceneTree scripts, import assets, load GLB/GLTF at runtime, inspect scenes and animations, save/convert resources, run GUT tests, and export builds. Use when a task needs Godot invoked from a shell (CI, agent shell, batch conversion, headless inspection), when you must read a model or animation without the editor import pipeline, when filtering harmless headless leak noise from real errors, or when finding the Godot binary installed via the Godots flatpak. Generic across any Godot 4.x project (paths are CLI args).
---

# Godot headless CLI

Invoke the Godot engine directly from a shell. Generic across any Godot 4.x
project: every project path is a CLI arg or an editable top-of-file const. For
Blender-side retargeting and the `extract_tracks` EditorScript step, use the
[blender-godot-pipeline](../blender-godot-pipeline/SKILL.md) skill instead; this
skill is about driving Godot itself.

## When to use

- Run Godot logic from a shell with no editor (agent shell, CI, batch jobs).
- Read a GLB/GLTF model or its animations WITHOUT the editor import pipeline.
- Import assets, inspect scenes, convert/save resources, run tests, or export.
- Separate real errors from the harmless headless dummy-renderer exit noise.

## Binary discovery

Do not hardcode a version path. The binary lives under the Godots flatpak;
newest match wins:

```
ls -1 ~/.var/app/io.github.MakovWait.Godots/data/godot/app_userdata/Godots/versions/*/Godot_v*_linux*.x86_64 | sort -V | tail -n1
```

`scripts/run_headless.sh` does this for you (override with `$GODOT_BIN`,
`--godot`, or `$GODOT_GLOB`). Full snippet + rationale: [reference.md](reference.md).

## Editor vs headless

| Want | Flags | Notes |
|------|-------|-------|
| Run a `SceneTree` `.gd` | `--headless --path <p> -s res://s.gd` | `_init()` runs; MUST `quit(code)` |
| Run an `EditorScript` | `--editor --path <p> -s res://e.gd` | needs editor context |
| Import assets | `--headless --path <p> --import` | or `--editor --quit` fallback |
| Open editor from agent shell | `setsid nohup <bin> -e --path <p> &` | else SIGKILL when the turn ends |

`--headless` runs fine in-shell. Launching the EDITOR from an agent shell gets
SIGKILLed unless detached. Prefer godot-mcp for live editor control.

## Recipes

Each points at a bundled script or a documented command. Details, flag tables,
GUT args, and export notes: [reference.md](reference.md).

- **Run a one-off script**: `scripts/run_headless.sh --project <dir> -s res://path/script.gd -- <args>`.
  Script extends `SceneTree`, works in `_init()`, ends with `quit(code)`.
- **Import assets**: `scripts/run_headless.sh --project <dir> --import`. Needed
  before code depends on `.import`ed assets; NOT needed for the runtime GLB path.
- **Load a GLB/GLTF at runtime** (the key headless trick): `GLTFDocument.append_from_file()`
  + `generate_scene()`. Skips the editor + `.godot/imported` cache races.
  Used by `scripts/inspect_resource.gd`.
- **Inspect a scene/GLB**: `scripts/run_headless.sh --project <dir> -s <skilldir>/scripts/inspect_resource.gd -- <target.glb|.tscn> [--tracks N] [--anim NAME]`.
  Prints node tree, animation clips, sample track paths. `-s` accepts an
  ABSOLUTE path, so bundled skill scripts (outside `res://`) run as-is; no copy
  into the project needed.
- **Save/convert resources**: `ResourceSaver.save()` inside a `SceneTree` script.
- **Run GUT tests**: `scripts/gut_run.sh --project <dir> -gdir=res://test`.
  Surfaces pass/fail + exit code.
- **Export a build**: `<bin> --headless --path <dir> --export-release "<preset>" <out>`.
  Requires an `export_presets.cfg`. See reference.md.

## Gotchas

| Symptom | Reality |
|---------|---------|
| `Pages in use`, `RID allocations ... leaked at exit` | harmless dummy-renderer shutdown noise, NOT failure. Filtered by run_headless.sh. Trust the exit code. |
| `Leaked instance` / `ObjectDB instances leaked` | same: benign headless shutdown noise. |
| Import hangs or gives stale assets | concurrent CLI `--import` races an OPEN editor's `.godot/imported` cache. Close the editor, or use the GLTFDocument runtime path. |
| Nothing renders | `--headless` uses a dummy rasterizer; no rendering by design. |

Source of truth = **exit code** + real stdout errors, never the leak lines.

## Bundled resources

- `scripts/run_headless.sh` discovers the binary, runs `--headless`, filters
  the harmless exit noise, preserves the real exit code. Takes `--project` and
  a script path or `--` passthrough of raw Godot args.
- `scripts/inspect_resource.gd` `SceneTree` inspector: loads a `.tscn` (loader)
  or `.glb` (GLTFDocument runtime) and prints tree, animations, track paths.
- `scripts/gut_run.sh` thin GUT wrapper; runs tests headless, reports pass/fail
  + exit code (delegates discovery/filtering to run_headless.sh).
- `reference.md` full CLI flag table, discovery snippet, GUT args, export notes,
  and the gotchas table.
