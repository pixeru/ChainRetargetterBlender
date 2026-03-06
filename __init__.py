bl_info = {
	"name": "Animation Importer",
	"author": "GitHub Copilot",
	"version": (1, 1, 0),
	"blender": (4, 0, 0),
	"location": "View3D > Sidebar > Animation Importer",
	"description": "Import an action from an FBX file onto the selected rig",
	"category": "Animation",
}

import os

import bpy
from bpy.props import StringProperty
from bpy.types import Operator, Panel
from bpy_extras.io_utils import ImportHelper


def _selected_rig(context):
	active = context.view_layer.objects.active
	if active and active.type == 'ARMATURE':
		return active

	selected_armatures = [obj for obj in context.selected_objects if obj.type == 'ARMATURE']
	if len(selected_armatures) == 1:
		return selected_armatures[0]

	return None


def _comparison_rig(context, target_rig):
	if target_rig is None:
		return None

	selected_armatures = [obj for obj in context.selected_objects if obj.type == 'ARMATURE' and obj != target_rig]
	if len(selected_armatures) == 1:
		return selected_armatures[0]

	return None


def _pick_action_slot(action, rig_object):
	if not hasattr(action, "slots"):
		return None

	suitable_types = {'OBJECT', 'UNSPECIFIED'}

	for slot in action.slots:
		if slot.target_id_type in suitable_types:
			return slot

	return action.slots[0] if len(action.slots) else None


def _assign_action_to_rig(rig_object, action):
	anim_data = rig_object.animation_data_create()

	slot = _pick_action_slot(action, rig_object)
	if slot is not None and hasattr(anim_data, "last_slot_identifier"):
		try:
			anim_data.last_slot_identifier = slot.identifier
		except (AttributeError, TypeError, ValueError):
			pass

	anim_data.action = action

	if slot is None:
		return

	if hasattr(anim_data, "action_slot_handle"):
		try:
			anim_data.action_slot_handle = slot.handle
		except (AttributeError, TypeError, ValueError):
			pass

	if hasattr(anim_data, "action_slot"):
		try:
			anim_data.action_slot = slot
		except (AttributeError, TypeError, ValueError):
			pass


def _remove_action_fcurve(action, fcurve):
	if hasattr(action, "fcurves"):
		action.fcurves.remove(fcurve)
		return

	for layer in getattr(action, "layers", []):
		for strip in getattr(layer, "strips", []):
			channelbag = getattr(strip, "channelbag", None)
			fcurves = getattr(channelbag, "fcurves", None)
			if fcurves is None:
				continue
			for candidate in list(fcurves):
				if candidate.as_pointer() == fcurve.as_pointer():
					fcurves.remove(candidate)
					return


def _sanitize_action_for_same_rig(action):
	if not hasattr(action, "fcurves"):
		return

	transform_paths = {
		"location",
		"rotation_euler",
		"rotation_quaternion",
		"rotation_axis_angle",
		"scale",
	}

	for fcurve in list(action.fcurves):
		data_path = fcurve.data_path

		# Remove object-level transforms so the destination rig keeps its existing size and placement.
		if data_path in transform_paths:
			_remove_action_fcurve(action, fcurve)
			continue

		# Remove pose bone scale keys so only motion is transferred.
		if data_path.startswith('pose.bones[') and data_path.endswith('.scale'):
			_remove_action_fcurve(action, fcurve)


def _mode_to_object(context):
	if context.mode == 'OBJECT':
		return

	active = context.view_layer.objects.active
	if active is None:
		return

	try:
		bpy.ops.object.mode_set(mode='OBJECT')
	except RuntimeError:
		pass


def _extract_imported_action_and_rig(new_objects, new_actions):
	imported_armatures = [obj for obj in new_objects if obj.type == 'ARMATURE']

	for armature_object in imported_armatures:
		anim_data = armature_object.animation_data
		if anim_data and anim_data.action:
			return anim_data.action, armature_object

	if new_actions:
		fallback_rig = imported_armatures[0] if imported_armatures else None
		return new_actions[0], fallback_rig

	return None, None


def _bone_compatibility_text_from_names(target_rig, imported_bone_names):
	if target_rig is None or imported_bone_names is None:
		return "Compatibility: unavailable"

	target_bones = {bone.name for bone in target_rig.data.bones}
	imported_total = len(imported_bone_names)

	if imported_total == 0:
		return "Compatibility: 0 of 0 bones, 0.0% compatible"

	matched = sum(1 for bone_name in imported_bone_names if bone_name in target_bones)
	percentage = (matched / imported_total) * 100.0
	return f"Compatibility: {matched} of {imported_total} bones, {percentage:.1f}% compatible"


def _bone_compatibility_text(target_rig, source_rig):
	if source_rig is None:
		return "Compatibility: unavailable"

	source_bone_names = [bone.name for bone in source_rig.data.bones]
	return _bone_compatibility_text_from_names(target_rig, source_bone_names)


def _remove_objects(objects):
	if not objects:
		return

	for obj in objects:
		try:
			bpy.data.objects.remove(obj, do_unlink=True)
		except RuntimeError:
			pass


def _remove_unused_ids(id_collection, names_to_consider, keep_names=()):
	keep_names = set(keep_names)
	for datablock in list(id_collection):
		if datablock.name not in names_to_consider or datablock.name in keep_names:
			continue
		if datablock.users != 0:
			continue
		try:
			id_collection.remove(datablock)
		except RuntimeError:
			pass


def _import_fbx_animation(filepath):
	before_objects = set(bpy.data.objects.keys())
	before_actions = set(bpy.data.actions.keys())
	before_armatures = set(bpy.data.armatures.keys())
	before_meshes = set(bpy.data.meshes.keys())
	before_materials = set(bpy.data.materials.keys())
	before_images = set(bpy.data.images.keys())
	before_collections = set(bpy.data.collections.keys())

	bpy.ops.import_scene.fbx(filepath=filepath, use_anim=True)

	new_objects = [bpy.data.objects[name] for name in bpy.data.objects.keys() if name not in before_objects]
	new_actions = [bpy.data.actions[name] for name in bpy.data.actions.keys() if name not in before_actions]
	new_armatures = set(bpy.data.armatures.keys()) - before_armatures
	new_meshes = set(bpy.data.meshes.keys()) - before_meshes
	new_materials = set(bpy.data.materials.keys()) - before_materials
	new_images = set(bpy.data.images.keys()) - before_images
	new_collections = set(bpy.data.collections.keys()) - before_collections

	imported_action, imported_rig = _extract_imported_action_and_rig(new_objects, new_actions)
	if imported_action is None:
		_remove_objects(new_objects)
		_remove_unused_ids(bpy.data.armatures, new_armatures)
		_remove_unused_ids(bpy.data.meshes, new_meshes)
		_remove_unused_ids(bpy.data.materials, new_materials)
		_remove_unused_ids(bpy.data.images, new_images)
		_remove_unused_ids(bpy.data.collections, new_collections)
		return None, None, 0

	imported_bone_names = None
	if imported_rig is not None:
		imported_bone_names = [bone.name for bone in imported_rig.data.bones]

	_remove_objects(new_objects)
	_remove_unused_ids(bpy.data.armatures, new_armatures)
	_remove_unused_ids(bpy.data.meshes, new_meshes)
	_remove_unused_ids(bpy.data.materials, new_materials)
	_remove_unused_ids(bpy.data.images, new_images)
	_remove_unused_ids(bpy.data.collections, new_collections)

	return imported_action, imported_bone_names, len(new_objects)


class ANIMATIONIMPORTER_OT_pick_source_file(Operator, ImportHelper):
	bl_idname = "animation_importer.pick_source_file"
	bl_label = "Choose Animation File"
	bl_description = "Choose an FBX file that contains the animation to import"
	bl_options = {'INTERNAL'}

	filename_ext = ".fbx"
	filter_glob: StringProperty(default="*.fbx", options={'HIDDEN'})

	def execute(self, context):
		context.scene.animation_importer_source = self.filepath
		context.scene.animation_importer_compatibility = "Compatibility: not checked yet"
		self.report({'INFO'}, f"Selected {os.path.basename(self.filepath)}")

		return {'FINISHED'}


class ANIMATIONIMPORTER_OT_load_action(Operator):
	bl_idname = "animation_importer.load_action"
	bl_label = "Load Animation"
	bl_description = "Import the chosen action and assign it to the selected rig"

	@classmethod
	def poll(cls, context):
		return context.scene is not None

	def execute(self, context):
		rig_object = _selected_rig(context)
		if rig_object is None:
			self.report({'ERROR'}, "Select one armature object to receive the animation")
			return {'CANCELLED'}

		filepath = context.scene.animation_importer_source

		if not filepath or not os.path.isfile(filepath):
			self.report({'ERROR'}, "Choose a valid source .fbx file first")
			return {'CANCELLED'}

		_mode_to_object(context)

		try:
			imported_action, imported_bone_names, imported_object_count = _import_fbx_animation(filepath)
		except RuntimeError as exc:
			context.scene.animation_importer_compatibility = "Compatibility: import failed"
			self.report({'ERROR'}, f"Failed to import FBX: {exc}")
			return {'CANCELLED'}

		if imported_action is None:
			context.scene.animation_importer_compatibility = "Compatibility: no importable action found"
			self.report({'ERROR'}, "The FBX did not create an importable action")
			return {'CANCELLED'}

		context.scene.animation_importer_compatibility = _bone_compatibility_text_from_names(rig_object, imported_bone_names)

		filename_stem = os.path.splitext(os.path.basename(filepath))[0]
		if imported_action.name in {'Armature', 'default', 'Take 001'}:
			imported_action.name = filename_stem

		_sanitize_action_for_same_rig(imported_action)
		imported_action.use_fake_user = True
		_assign_action_to_rig(rig_object, imported_action)

		frame_start, frame_end = imported_action.frame_range
		if frame_end > frame_start:
			context.scene.frame_start = int(frame_start)
			context.scene.frame_end = int(frame_end)

		self.report({'INFO'}, f"Loaded '{imported_action.name}' onto {rig_object.name} from FBX and removed {imported_object_count} temporary object(s). {context.scene.animation_importer_compatibility}")
		return {'FINISHED'}


class ANIMATIONIMPORTER_OT_check_open_rig_compatibility(Operator):
	bl_idname = "animation_importer.check_open_rig_compatibility"
	bl_label = "Check Open Rig Compatibility"
	bl_description = "Compare the active target rig against another selected armature already in the scene"

	@classmethod
	def poll(cls, context):
		target_rig = _selected_rig(context)
		comparison_rig = _comparison_rig(context, target_rig)
		return target_rig is not None and comparison_rig is not None

	def execute(self, context):
		target_rig = _selected_rig(context)
		comparison_rig = _comparison_rig(context, target_rig)

		if target_rig is None or comparison_rig is None:
			self.report({'ERROR'}, "Select the target rig as active and one other armature to compare")
			return {'CANCELLED'}

		context.scene.animation_importer_compatibility = _bone_compatibility_text(target_rig, comparison_rig)
		self.report({'INFO'}, f"Compared {target_rig.name} against {comparison_rig.name}. {context.scene.animation_importer_compatibility}")
		return {'FINISHED'}


class ANIMATIONIMPORTER_PT_sidebar(Panel):
	bl_label = "Animation Importer"
	bl_idname = "ANIMATIONIMPORTER_PT_sidebar"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_category = 'Animation Importer'

	def draw(self, context):
		layout = self.layout
		scene = context.scene
		rig_object = _selected_rig(context)
		comparison_rig = _comparison_rig(context, rig_object)

		col = layout.column(align=True)
		col.label(text="Source .fbx")
		col.prop(scene, "animation_importer_source", text="")

		col.separator()
		button_row = col.row()
		button_row.enabled = rig_object is not None and bool(scene.animation_importer_source)
		button_row.operator("animation_importer.load_action", icon='ACTION')

		compare_row = col.row()
		compare_row.enabled = comparison_rig is not None
		compare_row.operator("animation_importer.check_open_rig_compatibility", icon='ARMATURE_DATA')

		layout.separator()
		if rig_object is None:
			layout.label(text="Select one armature in the scene.", icon='ERROR')
		else:
			layout.label(text=f"Target rig: {rig_object.name}", icon='ARMATURE_DATA')
		if comparison_rig is not None:
			layout.label(text=f"Compare rig: {comparison_rig.name}", icon='BONE_DATA')

		layout.label(text="The FBX is imported temporarily to extract its action.", icon='INFO')
		layout.label(text="To compare an open rig, select the target rig and one other armature.", icon='INFO')
		layout.label(text="Imported action will appear in the Action Editor.", icon='INFO')
		layout.label(text=scene.animation_importer_compatibility, icon='BONE_DATA')


classes = (
	ANIMATIONIMPORTER_OT_pick_source_file,
	ANIMATIONIMPORTER_OT_load_action,
	ANIMATIONIMPORTER_OT_check_open_rig_compatibility,
	ANIMATIONIMPORTER_PT_sidebar,
)


def register():
	for cls in classes:
		bpy.utils.register_class(cls)

	bpy.types.Scene.animation_importer_source = StringProperty(
		name="Source FBX",
		description="FBX file that contains the source animation",
		subtype='FILE_PATH',
	)
	bpy.types.Scene.animation_importer_compatibility = StringProperty(
		name="Compatibility",
		description="Latest imported rig compatibility result",
		default="Compatibility: not checked yet",
	)


def unregister():
	del bpy.types.Scene.animation_importer_compatibility
	del bpy.types.Scene.animation_importer_source

	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)


if __name__ == "__main__":
	register()
