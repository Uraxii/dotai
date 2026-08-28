---
name: blender-godot-pipeline
description: Retarget and import external animation onto a Godot character's existing skeleton using headless Blender, without renaming the skeleton's bones or fighting Godot's humanoid retargeter. Use when bringing outside animation (Mixamo or any source rig) onto a game character, fixing or authoring models/animations in Blender for Godot, when arms come out in a wrong "guard" pose after retargeting, or when Godot's import BoneMap/Rest-Fixer would rename bones and break existing code and attachments.
---

# Blender-to-Godot animation pipeline

Bring animation from ANY source rig onto a Godot character's EXISTING skeleton,
keeping that skeleton's native bone names so existing bone references,
attachments, and code keep working. Everything is parameterized: supply your own
target GLB, source anim(s), bone map, skeleton path, and output dir.

## Pipeline

```
[target .glb] + [source anim(s)]
        |  scripts/retarget_bake.py  (Blender 5.x, headless)
        v
  rest-delta world transfer  ->  bake per-frame  ->  export .glb (named actions)
        |                                                   |
        v                                                   v
  validation PNGs (front / rear-3/4 / side)         re-import to verify action count
        |
        |  scripts/extract_tracks.gd  (Godot @tool EditorScript)
        v
  standalone Animation .tres, tracks pathed <skeleton>:<bone>
```

Core method (rest-delta, per mapped bone per frame):
`target_pose_world = (src_pose_world @ src_rest_world^-1) @ target_rest_world`,
then convert to the target bone's local pose and keyframe. Transfer ROTATION
only (optionally root translation). Do NOT also copy local rotation, or limbs
double-apply into a guard pose. See [reference.md](reference.md) for why this
beats local-copy and Godot's import-time BoneMap/Rest-Fixer.

## Workflow

1. **Retarget + bake + export + render** with the bundled Blender script. It is
   headless and needs a flatpak filesystem grant:
   ```
   flatpak run --filesystem=host org.blender.Blender --background \
     --python scripts/retarget_bake.py -- \
     --target-glb <char.glb> --src-fbx <name> <anim.fbx> \
     --bone-map <map.json> --out-glb <res_tree/out.glb> --render-dir <dir>
   ```
   Repeat `--src-fbx` per clip. For in-place idle/run add `--root-bone <hips>
   --keep-vertical-bob`. Full flag table + Mixamo scale/axis notes:
   [reference.md](reference.md). The script self-verifies by re-importing the
   GLB and printing the action count.
2. **Judge the validation PNGs** (front / rear-3/4 / side) that the script
   writes. Clean high-res frames beat a slow in-engine viewport for spotting a
   bad pose. If arms look bent/guarded, see Troubleshooting in reference.md.
3. **Ingest into Godot.** Put the output GLB under the project `res://` tree so
   Godot imports it. Then either:
   - Play the GLB's own AnimationPlayer clips directly (simplest), OR
   - Extract standalone `.tres` clips with `scripts/extract_tracks.gd` when
     consumers expect standalone resources or a bone subset. Configure its
     top-of-file consts (GLB path, out dir, skeleton path, clip/bone lists) and
     run it as an editor script. Pick which per reference.md.

## Bundled resources

- `scripts/retarget_bake.py` Blender headless retarget + bake + GLB export +
  validation renders. CLI-parameterized; no hardcoded project data.
- `scripts/extract_tracks.gd` Godot `@tool` EditorScript that writes standalone
  Animation `.tres` from an imported GLB. Configured via top-of-file consts.
- `scripts/bone_map.example.json` example Mixamo->Unreal-mannequin bone map.
  Copy and edit for your own source/target rigs.
- `reference.md` CLI flag tables, flatpak permission notes, method rationale,
  and a troubleshooting table (double-apply, scale, drift, permissions).

## Environment

Blender 5.1 flatpak (`org.blender.Blender`), always `--background` with a
`--filesystem` grant. Godot 4.6 via the "Godots" flatpak; use godot-mcp for
editor control when available. Throwaway scripts belong in `src/debug/`
(gitignored); GLB/asset outputs Godot imports must live under `res://`.
