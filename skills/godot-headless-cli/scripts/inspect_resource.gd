# inspect_resource.gd - general-purpose headless resource/scene/GLB inspector.
#
# A SceneTree script: run with `godot --headless --path <proj> -s res://.../inspect_resource.gd -- <target> [flags]`
# _init() runs, does its work, then quit(code). No editor needed.
#
# Target may be:
#   - res://path/to/scene.tscn      (loaded via ResourceLoader)
#   - res://path/to/model.glb       (loaded at RUNTIME via GLTFDocument, no import)
#   - an absolute/relative .glb path outside res:// (also via GLTFDocument)
#
# Prints: node tree, AnimationPlayer clip list, and a sample of track paths.
#
# Flags (after `--`):
#   --tracks <n>   max sample track paths per animation to print (default 8)
#   --anim <name>  only detail this one animation
#
# Exit codes: 0 ok, 2 bad args, 3 load failed.
extends SceneTree

const DEFAULT_TRACK_SAMPLE := 8

func _init() -> void:
	var args := _script_args()
	if args.is_empty():
		_err("no target given. pass a .tscn/.glb path after `--`.")
		quit(2)
		return

	var target: String = args[0]
	var track_sample := DEFAULT_TRACK_SAMPLE
	var only_anim := ""
	var i := 1
	while i < args.size():
		match args[i]:
			"--tracks":
				i += 1
				track_sample = int(args[i]) if i < args.size() else track_sample
			"--anim":
				i += 1
				only_anim = args[i] if i < args.size() else ""
		i += 1

	print("=== inspect_resource: ", target, " ===")
	var root := _load_target(target)
	if root == null:
		_err("failed to load target: " + target)
		quit(3)
		return

	print("\n--- node tree ---")
	_print_tree(root, 0)

	print("\n--- animations ---")
	_print_animations(root, only_anim, track_sample)

	print("\n=== done ===")
	quit(0)

# Collect args after the `--` separator that Godot forwards to the script.
func _script_args() -> PackedStringArray:
	return OS.get_cmdline_user_args()

# Runtime GLB load avoids the editor import pipeline and the .godot/imported
# cache races. .tscn/.tres go through the normal loader.
func _load_target(path: String) -> Node:
	var lower := path.to_lower()
	if lower.ends_with(".glb") or lower.ends_with(".gltf"):
		var doc := GLTFDocument.new()
		var state := GLTFState.new()
		var err := doc.append_from_file(path, state)
		if err != OK:
			_err("GLTFDocument.append_from_file failed: %d" % err)
			return null
		return doc.generate_scene(state)
	# Scene / packed resource path.
	if not ResourceLoader.exists(path):
		_err("ResourceLoader: path does not exist: " + path)
		return null
	var res := ResourceLoader.load(path)
	if res is PackedScene:
		return (res as PackedScene).instantiate()
	_err("loaded resource is not a PackedScene: " + str(res))
	return null

func _print_tree(node: Node, depth: int) -> void:
	print("  ".repeat(depth), "- ", node.name, " [", node.get_class(), "]")
	for child in node.get_children():
		_print_tree(child, depth + 1)

func _print_animations(root: Node, only_anim: String, track_sample: int) -> void:
	var players := _find_players(root)
	if players.is_empty():
		print("(no AnimationPlayer found)")
		return
	for player in players:
		print("AnimationPlayer: ", root.get_path_to(player))
		for anim_name in player.get_animation_list():
			if only_anim != "" and String(anim_name) != only_anim:
				continue
			var anim := player.get_animation(anim_name)
			print("  clip '", anim_name, "'  len=", anim.length,
				"s  tracks=", anim.get_track_count())
			var shown := 0
			for t in anim.get_track_count():
				if shown >= track_sample:
					print("    ... (", anim.get_track_count() - shown, " more)")
					break
				print("    [", t, "] ", anim.track_get_path(t))
				shown += 1

func _find_players(node: Node) -> Array[AnimationPlayer]:
	var out: Array[AnimationPlayer] = []
	if node is AnimationPlayer:
		out.append(node as AnimationPlayer)
	for child in node.get_children():
		out.append_array(_find_players(child))
	return out

func _err(msg: String) -> void:
	push_error("inspect_resource: " + msg)
	printerr("inspect_resource: ", msg)
