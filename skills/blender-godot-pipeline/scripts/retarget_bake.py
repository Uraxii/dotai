#!/usr/bin/env python3
"""Headless Blender retarget + bake + GLB export + validation renders.

Generic: retarget ANY source animation rig onto ANY target skeleton, using a
supplied bone-name map. The target skeleton's native bone names are preserved
(no rename to a humanoid profile), so a game's existing bone references keep
working.

Method: rest-delta world transfer. For each mapped bone, each frame:
    target_pose_world = (src_pose_world @ src_rest_world.inverted()) @ target_rest_world
then convert to the target bone's LOCAL pose and keyframe. This absorbs
differing rest poses (e.g. source T-pose vs target A-pose) and bone-roll
differences. We transfer ONLY the rest-delta rotation. We do NOT also copy the
source's local rotation on top: that is the classic double-apply bug (arms end
up in a "guard" pose).

Run (Blender 5.x flatpak, headless):
    flatpak run --filesystem=host org.blender.Blender --background \
        --python retarget_bake.py -- \
        --target-glb /abs/path/character.glb \
        --src-fbx idle /abs/path/Idle.fbx \
        --src-fbx run  /abs/path/Run.fbx \
        --bone-map /abs/path/bone_map.json \
        --out-glb /abs/path/res_tree/anims.glb \
        --render-dir /abs/path/validation

The `--filesystem=host` grant (or a targeted `--filesystem=<dir>`) is REQUIRED
or the sandbox cannot read/write your project files.

--bone-map JSON is a flat object mapping source bone name -> target bone name:
    { "mixamorig:LeftArm": "upperarm_l", ... }
Only listed bones are retargeted. Include arms/spine/legs/fingers as desired.
"""

import argparse
import json
import sys
from typing import Optional

import bpy
from mathutils import Matrix, Vector


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    # Args after the standalone "--" are ours; Blender ignores them.
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []

    p = argparse.ArgumentParser(description="Blender headless retarget + bake.")
    p.add_argument("--target-glb", required=True,
                   help="Target character GLB. Its skeleton + bone names are kept.")
    p.add_argument("--src-fbx", nargs=2, action="append", metavar=("ACTION", "PATH"),
                   required=True, help="Source anim: <action_name> <fbx_path>. Repeatable.")
    p.add_argument("--bone-map", required=True,
                   help="JSON file: {source_bone: target_bone}.")
    p.add_argument("--out-glb", required=True, help="Output GLB (put under res:// tree).")
    p.add_argument("--render-dir", default=None,
                   help="If set, write validation PNGs here.")
    p.add_argument("--root-bone", default=None,
                   help="Optional target root/hips bone for translation transfer.")
    p.add_argument("--keep-vertical-bob", action="store_true",
                   help="With --root-bone: keep vertical (Z) motion, strip horizontal drift.")
    p.add_argument("--src-scale", type=float, default=0.01,
                   help="Import scale for source FBX. Mixamo cm->m = 0.01 (default).")
    p.add_argument("--render-frame", type=int, default=None,
                   help="Frame to render for validation (default: mid-range).")
    return p.parse_args(argv)


# ---------------------------------------------------------------------------
# Scene helpers
# ---------------------------------------------------------------------------
def clear_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)


def find_armature() -> Optional[bpy.types.Object]:
    for obj in bpy.context.scene.objects:
        if obj.type == "ARMATURE":
            return obj
    return None


def import_target(glb_path: str) -> bpy.types.Object:
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=glb_path)
    arm = next((o for o in set(bpy.context.scene.objects) - before
                if o.type == "ARMATURE"), None)
    if arm is None:
        raise RuntimeError(f"No armature found in target GLB: {glb_path}")
    return arm


def import_source(fbx_path: str, scale: float) -> bpy.types.Object:
    before = set(bpy.context.scene.objects)
    # automatic_bone_orientation keeps Blender from re-rolling bones; global scale
    # normalises Mixamo-style cm/100x rigs and up-axis to Blender's Z-up metres.
    bpy.ops.import_scene.fbx(
        filepath=fbx_path,
        global_scale=scale,
        automatic_bone_orientation=True,
        use_anim=True,
    )
    src = next((o for o in set(bpy.context.scene.objects) - before
                if o.type == "ARMATURE"), None)
    if src is None:
        raise RuntimeError(f"No armature found in source FBX: {fbx_path}")
    return src


# ---------------------------------------------------------------------------
# Rest-delta retarget core
# ---------------------------------------------------------------------------
def rest_world(arm: bpy.types.Object, bone_name: str) -> Optional[Matrix]:
    """World-space REST matrix of a bone (armature matrix @ bone rest matrix)."""
    bone = arm.data.bones.get(bone_name)
    if bone is None:
        return None
    return arm.matrix_world @ bone.matrix_local


def pose_to_basis(pbone: bpy.types.PoseBone, pose_obj: Matrix) -> Matrix:
    """Invert Blender's pose-chain formula to recover a bone's local basis matrix
    from its object-space pose matrix."""
    if pbone.parent is not None:
        rest_delta = pbone.parent.bone.matrix_local.inverted() @ pbone.bone.matrix_local
        return (pbone.parent.matrix @ rest_delta).inverted() @ pose_obj
    return pbone.bone.matrix_local.inverted() @ pose_obj


def retarget_action(
    src: bpy.types.Object,
    tgt: bpy.types.Object,
    bone_map: dict,
    action_name: str,
    root_bone: Optional[str],
    keep_vertical_bob: bool,
) -> bpy.types.Action:
    """Bake a retargeted Action onto the TARGET armature for the given source anim."""
    scene = bpy.context.scene
    src_action = src.animation_data.action if src.animation_data else None
    if src_action is None:
        raise RuntimeError(f"Source '{action_name}' has no action/animation.")

    f_start, f_end = (int(src_action.frame_range[0]), int(src_action.frame_range[1]))
    scene.frame_start, scene.frame_end = f_start, f_end

    # Precompute rest matrices (constant across frames).
    src_rest = {s: rest_world(src, s) for s in bone_map}
    tgt_rest = {t: rest_world(tgt, t) for t in bone_map.values()}

    # Fresh target action.
    tgt.animation_data_create()
    action = bpy.data.actions.new(name=action_name)
    tgt.animation_data.action = action

    root_ref_loc = None  # first-frame root world location, to strip drift.

    for frame in range(f_start, f_end + 1):
        scene.frame_set(frame)

        for src_name, tgt_name in bone_map.items():
            sr, tr = src_rest.get(src_name), tgt_rest.get(tgt_name)
            if sr is None or tr is None:
                continue
            src_pbone = src.pose.bones.get(src_name)
            tgt_pbone = tgt.pose.bones.get(tgt_name)
            if src_pbone is None or tgt_pbone is None:
                continue

            src_pose_world = src.matrix_world @ src_pbone.matrix
            # Rest-delta world transfer.
            target_world = (src_pose_world @ sr.inverted()) @ tr

            # Rotation only (unless this is the designated root bone).
            do_translation = (root_bone is not None and tgt_name == root_bone)
            if not do_translation:
                # Replace translation part with the rest translation: rotation-only.
                loc, _rot, _scl = target_world.decompose()
                # Keep the bone's rest world location; only orientation is transferred.
                rest_loc = tr.to_translation()
                target_world = Matrix.Translation(rest_loc) @ \
                    target_world.to_quaternion().to_matrix().to_4x4()

            # Convert world -> target bone LOCAL (basis) pose.
            # Blender: pose.matrix (object space) =
            #   parent.matrix @ parent.bone.matrix_local^-1 @ bone.matrix_local @ basis
            # Solve for basis. Everything below is armature-OBJECT space.
            pose_obj = tgt.matrix_world.inverted() @ target_world
            local = pose_to_basis(tgt_pbone, pose_obj)

            if do_translation:
                world_loc = target_world.to_translation()
                if root_ref_loc is None:
                    root_ref_loc = world_loc.copy()
                if keep_vertical_bob:
                    # Strip horizontal drift, keep vertical (Z) bob.
                    world_loc.x = root_ref_loc.x
                    world_loc.y = root_ref_loc.y
                else:
                    world_loc = root_ref_loc.copy()
                target_world = Matrix.Translation(world_loc) @ \
                    target_world.to_quaternion().to_matrix().to_4x4()
                pose_obj = tgt.matrix_world.inverted() @ target_world
                local = pose_to_basis(tgt_pbone, pose_obj)
                tgt_pbone.location = local.to_translation()
                tgt_pbone.keyframe_insert("location", frame=frame)

            tgt_pbone.rotation_mode = "QUATERNION"
            tgt_pbone.rotation_quaternion = local.to_quaternion()
            tgt_pbone.keyframe_insert("rotation_quaternion", frame=frame)

    return action


# ---------------------------------------------------------------------------
# Export + render
# ---------------------------------------------------------------------------
def export_glb(out_path: str) -> None:
    bpy.ops.export_scene.gltf(
        filepath=out_path,
        export_format="GLB",
        export_yup=True,
        export_animations=True,
        export_animation_mode="ACTIONS",  # one clip per Action, named.
        export_nla_strips=True,
    )


def verify_glb(out_path: str) -> int:
    """Re-import the exported GLB in a clean scene; return action count."""
    clear_scene()
    bpy.ops.import_scene.gltf(filepath=out_path)
    return len(bpy.data.actions)


def render_validation(tgt: bpy.types.Object, out_dir: str, frame: Optional[int]) -> None:
    """Render front / rear-3/4 / side PNGs of the character at one frame."""
    import os
    scene = bpy.context.scene
    if frame is None:
        frame = (scene.frame_start + scene.frame_end) // 2
    scene.frame_set(frame)

    # Simple camera + sun so a human can judge the pose on clean frames.
    cam_data = bpy.data.cameras.new("val_cam")
    cam = bpy.data.objects.new("val_cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    sun = bpy.data.objects.new("val_sun", bpy.data.lights.new("val_sun", "SUN"))
    scene.collection.objects.link(sun)

    center = tgt.matrix_world.to_translation() + Vector((0, 0, 1.0))
    scene.render.resolution_x = 1080
    scene.render.resolution_y = 1440
    scene.render.image_settings.file_format = "PNG"

    views = {
        "front": Vector((0, -4, 1.2)),
        "rear_3q": Vector((3, 3, 1.4)),
        "side": Vector((4, 0, 1.2)),
    }
    for name, pos in views.items():
        cam.location = pos
        direction = center - cam.location
        cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = os.path.join(out_dir, f"validate_{name}.png")
        bpy.ops.render.render(write_still=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    args = parse_args()
    with open(args.bone_map, "r", encoding="utf-8") as fh:
        bone_map = json.load(fh)
    if not isinstance(bone_map, dict) or not bone_map:
        raise SystemExit("bone-map JSON must be a non-empty {source: target} object.")

    clear_scene()
    tgt = import_target(args.target_glb)
    print(f"[retarget] target armature: {tgt.name} "
          f"({len(tgt.data.bones)} bones)")

    for action_name, fbx_path in args.src_fbx:
        src = import_source(fbx_path, args.src_scale)
        print(f"[retarget] baking '{action_name}' from {fbx_path}")
        retarget_action(src, tgt, bone_map, action_name,
                        args.root_bone, args.keep_vertical_bob)
        # Remove source armature before the next import to avoid name clashes.
        bpy.data.objects.remove(src, do_unlink=True)

    export_glb(args.out_glb)
    print(f"[retarget] exported GLB -> {args.out_glb}")

    # Render BEFORE verify_glb wipes the scene. tgt is still valid post-export.
    if args.render_dir:
        render_validation(tgt, args.render_dir, args.render_frame)
        print(f"[retarget] validation renders -> {args.render_dir}")

    count = verify_glb(args.out_glb)
    print(f"[retarget] re-import OK: {count} actions in {args.out_glb}")
    if count < len(args.src_fbx):
        print(f"[retarget] WARNING: expected >= {len(args.src_fbx)} actions, "
              f"got {count}. Check export_animation_mode / NLA settings.")


if __name__ == "__main__":
    main()
