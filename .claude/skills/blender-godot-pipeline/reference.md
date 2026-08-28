# Blender-to-Godot pipeline: reference

Full detail behind the lean [SKILL.md](SKILL.md). Nothing here is tied to a
specific project: supply your own GLB, source anim, bone map, and skeleton path.

## Flatpak permission notes (this machine)

Blender 5.1 runs as a flatpak. The sandbox cannot see arbitrary paths unless
granted. Every headless call needs a filesystem grant:

```
flatpak run --filesystem=host org.blender.Blender --background --python <s>.py -- <args>
```

- `--filesystem=host` grants all host paths (simplest). For least privilege use
  a targeted grant like `--filesystem=/abs/project/dir`.
- Always pass `--background` (headless, no GUI, exits when the script returns).
- Missing/insufficient grant symptom: `Permission denied` / cannot read the
  input GLB/FBX or cannot write the output.
- The flatpak has a PRIVATE `/tmp`: host `/tmp` paths are invisible even with
  `--filesystem=host` (symptom: `Python file ... could not be opened`). Keep
  script and I/O paths under the project tree or your home dir, not `/tmp`.

Godot 4.6 runs via the "Godots" flatpak manager (see the user's global instructions
file for the versioned binary path). The `.gd` here is an EditorScript run from inside
the open editor, or via godot-mcp; it is not a headless CLI script.

## retarget_bake.py CLI

| Flag | Required | Meaning |
| --- | --- | --- |
| `--target-glb PATH` | yes | Character GLB. Its skeleton + native bone names are kept. |
| `--src-fbx NAME PATH` | yes | Source anim: action name + FBX. Repeat per clip. |
| `--bone-map PATH` | yes | JSON `{source_bone: target_bone}`. Only listed bones retarget. |
| `--out-glb PATH` | yes | Output GLB. Put under the project `res://` tree so Godot imports it. |
| `--render-dir PATH` | no | Write front / rear-3/4 / side validation PNGs here. |
| `--root-bone NAME` | no | Target hips/root bone to also transfer TRANSLATION. |
| `--keep-vertical-bob` | no | With `--root-bone`: keep Z bob, strip horizontal drift (idle/run in place). |
| `--src-scale FLOAT` | no | Source FBX import scale. Mixamo cm->m = `0.01` (default). |
| `--render-frame INT` | no | Frame to render (default: mid-range). |

### Example (Mixamo -> Unreal mannequin)

```
flatpak run --filesystem=host org.blender.Blender --background \
  --python scripts/retarget_bake.py -- \
  --target-glb /abs/project/res_tree/mannequin.glb \
  --src-fbx idle /abs/anims/Idle.fbx \
  --src-fbx run  /abs/anims/Running.fbx \
  --bone-map scripts/bone_map.example.json \
  --out-glb /abs/project/res_tree/character_anims.glb \
  --render-dir /abs/project/debug/validation \
  --root-bone pelvis --keep-vertical-bob
```

The example map `scripts/bone_map.example.json` is Mixamo->Unreal-mannequin.
Copy and edit it for any other source/target pair; keys are source bones,
values are the target skeleton's own bone names.

## extract_tracks.gd

An `@tool extends EditorScript`. Configure the consts at the top:

- `GLB_PATH` imported GLB under `res://`.
- `OUT_DIR` where `.tres` clips land.
- `SKELETON_PATH` skeleton node path baked INTO the track paths
  (`<SKELETON_PATH>:<bone>`). Default `Armature/Skeleton3D`; change per rig.
- `CLIP_NAMES` clips to extract (`[]` = all).
- `BONE_FILTER` bones to keep (`[]` = all).

Run it with the script open in the editor via File > Run, or through godot-mcp.

## Why the rest-delta method (and not local-copy or Godot's retargeter)

- Source and target REST poses differ (e.g. Mixamo T-pose vs an A-pose rig).
  Copying source LOCAL rotations straight over ignores that difference and the
  limbs come out wrong.
- Rest-delta world transfer,
  `target_pose_world = (src_pose_world @ src_rest_world^-1) @ target_rest_world`,
  measures how far the source bone moved FROM ITS OWN REST and reapplies that
  to the target's rest. It absorbs rest and bone-roll differences.
- Godot's import-time BoneMap / Bone Renamer / Rest Fixer would rename the
  skeleton to `SkeletonProfileHumanoid` bone names, breaking every existing
  bone reference, attachment, and code path. We keep the target's native names
  by retargeting in Blender instead.

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| Arms in a "guard"/bent pose | Double-apply: local rotation copied on top of the rest-delta | Use rotation-only rest-delta (this script already does); do not also copy source local rotation. |
| Character is giant or tiny | Wrong source import scale / up-axis | Set `--src-scale` (Mixamo = `0.01`); import uses `automatic_bone_orientation`. |
| Character walks off / drifts | Root translation copied raw | Add `--keep-vertical-bob`, or omit `--root-bone` for pure in-place. |
| `Permission denied` on I/O | Missing flatpak grant | Add `--filesystem=host` (or a targeted `--filesystem=<dir>`). |
| Re-import shows fewer actions than clips | glTF export animation mode/NLA | Script uses `export_animation_mode=ACTIONS` + `export_nla_strips`; check the warning it prints. |
| Bones missing in retarget | Name absent in target skeleton or map | Verify bone-map values match the target skeleton's actual bone names. |
| `.tres` tracks point at wrong node | `SKELETON_PATH` mismatch | Set it to the skeleton path in the CONSUMING scene, not the GLB's. |
