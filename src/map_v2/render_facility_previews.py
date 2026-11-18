"""Live Blender thumbnail render. Temporary scene; preserve original cameras and geometry."""
import bpy
import json
from mathutils import Vector

BASE = '/path/to/wulanchabu-energy-map'
IDS = ['DC_004', 'DC_005', 'DC_006', 'HUB_011', 'STORE_012', 'DEMO_013',
       'AGRI_014', 'AGRI_015', 'AGRI_016', 'AGRI_017', 'AGRI_018', 'DRY_019']
original = bpy.context.window.scene
scene = bpy.data.scenes.new('设施预览临时渲染')
scene.render.engine = original.render.engine
scene.render.resolution_x = 640
scene.render.resolution_y = 400
scene.render.resolution_percentage = 100
scene.render.film_transparent = True
scene.render.image_settings.file_format = next(i.identifier for i in bpy.types.ImageFormatSettings.bl_rna.properties['file_format'].enum_items if i.identifier == 'PNG')
scene.world = original.world
data = bpy.data.cameras.new('设施预览临时相机')
camera = bpy.data.objects.new('设施预览临时相机', data)
data.type = next(i.identifier for i in bpy.types.Camera.bl_rna.properties['type'].enum_items if i.identifier == 'ORTHO')
data.clip_end = 50000
scene.collection.objects.link(camera)
scene.camera = camera
sun_data = bpy.data.lights.new('设施预览临时光源', type=next(i.identifier for i in bpy.types.Light.bl_rna.properties['type'].enum_items if i.identifier == 'SUN'))
sun_data.energy = 3
sun = bpy.data.objects.new('设施预览临时光源', sun_data)
sun.rotation_euler = (.35, -.45, -.4)
scene.collection.objects.link(sun)
receipt = []
try:
    bpy.context.window.scene = scene
    for fid in IDS:
        root = bpy.data.objects[fid]
        members = [root] + [o for o in root.children_recursive if not o.hide_render and not o.get('superseded_by')]
        for o in members:
            scene.collection.objects.link(o)
        pad = bpy.data.objects[fid + ' | 场坪']
        scale = max(pad.dimensions.x * 1.3, pad.dimensions.y * 1.8)
        target = root.matrix_world.translation + Vector((0, 0, 7))
        camera.location = target + Vector((scale * .42, -scale * .7, scale * .65))
        camera.rotation_euler = (target - camera.location).to_track_quat('-Z','Y').to_euler()
        data.ortho_scale = scale
        scene.render.filepath = BASE + '/web/map-viewer/assets/facilities-v1/' + fid + '.png'
        result = bpy.ops.render.render(write_still=True)
        assert 'FINISHED' in result
        receipt.append({'object_id': fid, 'path': scene.render.filepath})
        for o in members:
            scene.collection.objects.unlink(o)
finally:
    bpy.context.window.scene = original
    bpy.data.scenes.remove(scene)
    bpy.data.objects.remove(camera, do_unlink=True)
    bpy.data.objects.remove(sun, do_unlink=True)
    bpy.data.cameras.remove(data)
    bpy.data.lights.remove(sun_data)
print(json.dumps({'previews': receipt}, ensure_ascii=False))
