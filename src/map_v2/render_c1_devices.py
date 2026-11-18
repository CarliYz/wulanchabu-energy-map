"""Render the existing C1 child entities in the user's live Blender."""
import bpy
import json
from mathutils import Vector

BASE = '/path/to/wulanchabu-energy-map'
original = bpy.context.window.scene
assert not bpy.data.is_dirty, 'Reconcile user edits before this render batch'
root = bpy.data.objects['AGRI_018']
def object_name(obj):
    return obj.name


entities = sorted([o for o in root.children if o.get('label')], key=object_name)
assert len(entities) == 11 and root.get('m8_revision') == 'c1-dual-loop-v1'
scene = bpy.data.scenes.new('C1子设备预览临时渲染')
scene.render.engine = original.render.engine
scene.render.resolution_x, scene.render.resolution_y = 640, 400
scene.render.resolution_percentage = 100
scene.render.film_transparent = True
scene.render.image_settings.file_format = next(i.identifier for i in bpy.types.ImageFormatSettings.bl_rna.properties['file_format'].enum_items if i.identifier == 'PNG')
scene.world = original.world
data = bpy.data.cameras.new('C1子设备临时相机')
camera = bpy.data.objects.new('C1子设备临时相机', data)
data.type = next(i.identifier for i in bpy.types.Camera.bl_rna.properties['type'].enum_items if i.identifier == 'ORTHO')
data.clip_start, data.clip_end = .01, 50000
scene.collection.objects.link(camera)
scene.camera = camera
sun_data = bpy.data.lights.new('C1子设备临时光源', type=next(i.identifier for i in bpy.types.Light.bl_rna.properties['type'].enum_items if i.identifier == 'SUN'))
sun_data.energy = 3
sun = bpy.data.objects.new('C1子设备临时光源', sun_data)
sun.rotation_euler = (.35, -.45, -.4)
scene.collection.objects.link(sun)
receipt = []
try:
    bpy.context.window.scene = scene
    for entity in entities:
        members = [root, entity] + [o for o in entity.children_recursive if not o.hide_render]
        for o in members:
            scene.collection.objects.link(o)
        bpy.context.view_layer.update()
        points = [o.matrix_world @ Vector(p) for o in members if o.type in {'MESH', 'CURVE'} for p in o.bound_box]
        low = Vector(tuple(min(p[i] for p in points) for i in range(3)))
        high = Vector(tuple(max(p[i] for p in points) for i in range(3)))
        target = (low + high) / 2
        scale = max((high - low).length * 1.3, 7)
        camera.location = target + Vector((scale*.42, -scale*.7, scale*.65))
        camera.rotation_euler = (target-camera.location).to_track_quat('-Z','Y').to_euler()
        data.ortho_scale = scale
        scene.render.filepath = BASE + '/web/map-viewer/assets/c1-devices-v1/' + entity.name + '.png'
        result = bpy.ops.render.render(write_still=True)
        assert 'FINISHED' in result
        receipt.append({'object_id': entity.name, 'path': scene.render.filepath,
                        'model_revision': root['m8_revision'], 'width': 640, 'height': 400})
        for o in members:
            scene.collection.objects.unlink(o)
finally:
    bpy.context.window.scene = original
    bpy.data.scenes.remove(scene)
    bpy.data.objects.remove(camera, do_unlink=True)
    bpy.data.objects.remove(sun, do_unlink=True)
    bpy.data.cameras.remove(data)
    bpy.data.lights.remove(sun_data)
bpy.context.window.scene = bpy.data.scenes['05 | 水培育苗']
bpy.ops.wm.save_as_mainfile(filepath=BASE+'/outputs/c1-devices-v1/乌兰察布_C1子设备联动_v1.blend')
print(json.dumps({'previews': receipt, 'saved': bpy.data.filepath, 'dirty': bpy.data.is_dirty}, ensure_ascii=False))
