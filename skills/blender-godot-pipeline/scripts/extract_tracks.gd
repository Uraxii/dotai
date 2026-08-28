@tool
extends EditorScript
## Extract animation clips from an imported GLB into standalone Animation .tres.
##
## Generic + reusable: nothing here is project-specific. Fill in the CONSTS
## below, then in the Godot editor run:  File > Run (or the Editor Script runner)
## with this script open. It loads the GLB scene, finds its AnimationPlayer,
## and for each wanted clip writes a standalone Animation resource whose tracks
## are re-pathed to <SKELETON_PATH>:<bone>. Existing consumers that reference
## those bone paths load the .tres unchanged, so no game code needs editing.
##
## Why extract instead of playing the GLB's own clips directly?
##   Extract  -> when consumers expect standalone Animation resources, want to
##               keep only a subset of bones, or blend clips from many GLBs.
##   Play GLB -> when you can just instance the imported scene and use its
##               AnimationPlayer as-is; simpler, but couples you to the GLB.

# --- CONFIGURE PER PROJECT --------------------------------------------------

## Imported GLB scene (res:// path). Must live under the project tree.
const GLB_PATH := "res://path/to/anims.glb"

## Where to write the .tres clips.
const OUT_DIR := "res://animations/"

## Skeleton node path INSIDE the extracted Animation tracks. This is the target
## skeleton's path in whatever scene will consume the clip, not the GLB's.
## Common Godot default shown; change if your rig differs.
const SKELETON_PATH := "Armature/Skeleton3D"

## Clip names to extract. Must match the Action names baked into the GLB.
## Leave empty [] to extract every clip found in the AnimationPlayer.
const CLIP_NAMES: Array[String] = []

## Bone names to keep. Leave empty [] to keep all bones present in the clip.
const BONE_FILTER: Array[String] = []

# ---------------------------------------------------------------------------

func _run() -> void:
	var packed: PackedScene = load(GLB_PATH)
	if packed == null:
		push_error("Could not load GLB: %s" % GLB_PATH)
		return
	var root: Node = packed.instantiate()
	var player: AnimationPlayer = _find_player(root)
	if player == null:
		push_error("No AnimationPlayer in %s" % GLB_PATH)
		root.free()
		return

	var wanted: Array[String] = CLIP_NAMES
	if wanted.is_empty():
		wanted = []
		for n in player.get_animation_list():
			wanted.append(n)

	var dir := DirAccess.open("res://")
	if not DirAccess.dir_exists_absolute(OUT_DIR):
		DirAccess.make_dir_recursive_absolute(OUT_DIR)

	for clip_name in wanted:
		if not player.has_animation(clip_name):
			push_warning("Clip not found, skipping: %s" % clip_name)
			continue
		var src: Animation = player.get_animation(clip_name)
		var out := _rebuild_clip(src)
		var path := OUT_DIR.path_join("%s.tres" % clip_name)
		var err := ResourceSaver.save(out, path)
		if err == OK:
			print("Wrote %s (%d tracks)" % [path, out.get_track_count()])
		else:
			push_error("Save failed (%d): %s" % [err, path])

	root.free()


func _find_player(node: Node) -> AnimationPlayer:
	if node is AnimationPlayer:
		return node
	for child in node.get_children():
		var found := _find_player(child)
		if found != null:
			return found
	return null


## Copy a source Animation, re-pathing bone tracks to SKELETON_PATH:<bone> and
## dropping bones not in BONE_FILTER (when set).
func _rebuild_clip(src: Animation) -> Animation:
	var out := Animation.new()
	out.length = src.length
	out.loop_mode = src.loop_mode
	out.step = src.step

	for i in src.get_track_count():
		var path := src.track_get_path(i)      # e.g. "Armature/Skeleton3D:upperarm_l"
		var bone := String(path.get_concatenated_subnames())
		if bone.is_empty():
			continue  # not a bone/subname track
		if not BONE_FILTER.is_empty() and not BONE_FILTER.has(bone):
			continue

		var new_idx := out.add_track(src.track_get_type(i))
		out.track_set_path(new_idx, NodePath("%s:%s" % [SKELETON_PATH, bone]))
		out.track_set_interpolation_type(new_idx, src.track_get_interpolation_type(i))

		for k in src.track_get_key_count(i):
			var t := src.track_get_key_time(i, k)
			var v: Variant = src.track_get_key_value(i, k)
			match src.track_get_type(i):
				Animation.TYPE_POSITION_3D, Animation.TYPE_ROTATION_3D, \
				Animation.TYPE_SCALE_3D:
					out.track_insert_key(new_idx, t, v)
				_:
					out.track_insert_key(new_idx, t, v)
	return out
