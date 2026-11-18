"""Save the full scene and export only C1 with ownership/port extras."""
import bpy
from mathutils import Vector

BASE = '/path/to/wulanchabu-energy-map'
root = bpy.data.objects['AGRI_018']
assert root.get('m8_revision') == 'c1-dual-loop-v1'
scene = bpy.data.scenes['05 | 水培育苗']
bpy.context.window.scene = scene
camera = bpy.data.objects.get('M8_CAMERA | C1验收')
if camera is None:
    data = bpy.data.cameras.new('M8_CAMERA | C1验收')
    camera = bpy.data.objects.new('M8_CAMERA | C1验收', data)
    scene.collection.objects.link(camera)
camera.data.type = next(i.identifier for i in bpy.types.Camera.bl_rna.properties['type'].enum_items if i.identifier == 'ORTHO')
camera.location = root.matrix_world.translation + Vector((145,-210,175))
target = root.matrix_world.translation + Vector((0,-5,2))
camera.rotation_euler = (target-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.ortho_scale = 240
camera.data.clip_start = .1
camera.data.clip_end = 20000
scene.camera = camera
scene.render.resolution_x = 1600
scene.render.resolution_y = 1000
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = next(i.identifier for i in bpy.types.ImageFormatSettings.bl_rna.properties['file_format'].enum_items if i.identifier == 'PNG')
scene.render.filepath = BASE+'/web/map-viewer/assets/c1-v1/overview.png'
bpy.ops.wm.save_as_mainfile(filepath=BASE+'/outputs/m8-c1/AGRI_018_dual_loop_v1.blend')
for o in bpy.context.view_layer.objects:
    o.select_set(False)
selected = [root] + [o for o in root.children_recursive if not o.hide_render and not o.get('superseded_by')]
for o in selected:
    o.select_set(True)
bpy.context.view_layer.objects.active = root
bpy.ops.export_scene.gltf(filepath=BASE+'/web/map-viewer/assets/c1-v1/AGRI_018.glb',
    export_format='GLB', use_selection=True, use_active_scene=True,
    export_apply=True, export_extras=True,
    export_cameras=False, export_lights=False)
for o in bpy.context.selected_objects:
    o.select_set(False)
root.select_set(True)
bpy.context.view_layer.objects.active=root
print({'saved':bpy.data.filepath,'glb_selected':len(selected),'render_path':scene.render.filepath})
