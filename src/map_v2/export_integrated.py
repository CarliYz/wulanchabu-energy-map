"""Export one combined, georeferenced facility asset from the live integrated copy."""
import bpy
import json
from mathutils import Vector

BASE = '/path/to/wulanchabu-energy-map'
PARENTS = ['DC_004','DC_005','DC_006','HUB_011','STORE_012','DEMO_013',
           'AGRI_014','AGRI_015','AGRI_016','AGRI_017','AGRI_018','DRY_019']
is_sensor = bpy.data.filepath.endswith('/m14-sensors-integrated-v1/乌兰察布_测点整合场景_v1.blend')
is_connected = is_sensor or bpy.data.filepath.endswith('/m12-connected-v1/乌兰察布_连接整合场景_v1.blend')
assert is_connected or bpy.data.filepath.endswith('/m11-integrated-v1/乌兰察布_整合场景_v1.blend')
blend_path = bpy.data.filepath
asset_folder = 'integrated-v3' if is_sensor else 'integrated-v2' if is_connected else 'integrated-v1'
scene = bpy.data.scenes.get('06 | 全区整合交互')
if scene is None:
    scene = bpy.data.scenes['05 | 水培育苗'].copy()
    scene.name = '06 | 全区整合交互'
bpy.context.window.scene = scene
scene.camera = bpy.data.scenes['01 | 地理总览'].camera
selected = set()
for fid in PARENTS:
    root = bpy.data.objects[fid]
    selected.add(root)
    selected.update(o for o in root.children_recursive if not o.hide_render and not o.get('superseded_by'))
for name in ['M9 | A/B 末端设备补模','M10 | 系统设备补模','M11 | B区真实父设施末端'] + (['M12 | 候选端口与连接'] if is_connected else []):
    selected.update(o for o in bpy.data.collections[name].objects if not o.hide_render and not o.get('superseded_by'))
selected = {o for o in selected if o.type in {'MESH','CURVE','EMPTY','FONT'}}
for obj in selected:
    assert obj.name in scene.objects, obj.name
for obj in scene.objects:
    obj.select_set(obj in selected)
bpy.context.view_layer.objects.active = bpy.data.objects['HUB_011']
converted = []
try:
    # glTF exports Blender meshes; curve-only nodes otherwise lose their pipes.
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for original in selected:
        if original.type not in {'CURVE','FONT'}:
            continue
        data = bpy.data.meshes.new_from_object(original.evaluated_get(depsgraph))
        if not data.vertices:
            bpy.data.meshes.remove(data)
            continue
        obj = bpy.data.objects.new(original.name+' | GLB mesh',data)
        scene.collection.objects.link(obj)
        obj.parent = original
        for key,value in original.items():
            obj[key] = value
        obj.select_set(True)
        original.select_set(False)
        converted.append(obj)
    result = bpy.ops.export_scene.gltf(
        filepath=BASE+'/web/map-viewer/assets/'+asset_folder+'/facilities.glb',
        export_format='GLB', use_selection=True, use_active_scene=True,
        export_apply=True, export_extras=True, export_cameras=False, export_lights=False)
    assert 'FINISHED' in result
finally:
    converted_count = len(converted)
    for obj in converted:
        data = obj.data
        bpy.data.objects.remove(obj,do_unlink=True)
        bpy.data.meshes.remove(data)
# Render scene shares only the chosen geometry, map and routes; no stale screen HUDs.
review_name = 'M14 | 整合验收渲染' if is_sensor else 'M12 | 连接验收渲染' if is_connected else 'M11 | 整合验收渲染'
review = bpy.data.scenes.get(review_name) or bpy.data.scenes.new(review_name)
review.world = scene.world
review.render.engine = scene.render.engine
for obj in selected:
    if obj.name not in review.objects:
        review.collection.objects.link(obj)
for name in ['01 DEM真实地形 | 1x','02 规划分区 | 待核','05 供回水管网 | 候选']:
    for obj in bpy.data.collections[name].objects:
        if obj.name not in review.objects and not obj.hide_render:
            review.collection.objects.link(obj)
for obj in scene.objects:
    if obj.type=='LIGHT' and obj.name not in review.objects:
        review.collection.objects.link(obj)
camera_data = bpy.data.cameras.get('M11 | 验收相机') or bpy.data.cameras.new('M11 | 验收相机')
camera = bpy.data.objects.get('M11 | 验收相机') or bpy.data.objects.new('M11 | 验收相机',camera_data)
if camera.name not in review.objects:
    review.collection.objects.link(camera)
camera_data.type = next(i.identifier for i in bpy.types.Camera.bl_rna.properties['type'].enum_items if i.identifier=='ORTHO')
camera_data.clip_end = 50000
camera_data.ortho_scale = 7400
target = Vector((-1400,1900,150))
camera.location = target + Vector((1500,-3500,5600))
camera.rotation_euler = (target-camera.location).to_track_quat('-Z','Y').to_euler()
review.camera = camera
review.render.resolution_x = 1440
review.render.resolution_y = 1000
review.render.resolution_percentage = 100
review.render.image_settings.file_format = next(i.identifier for i in bpy.types.ImageFormatSettings.bl_rna.properties['file_format'].enum_items if i.identifier=='PNG')
for obj in scene.objects:
    obj.select_set(False)
bpy.data.objects['AGRI_016'].select_set(True)
bpy.context.view_layer.objects.active = bpy.data.objects['AGRI_016']
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.region_3d.view_perspective = 'PERSP'
            area.spaces.active.region_3d.view_location = Vector((-1400,1900,150))
            area.spaces.active.region_3d.view_distance = 7800
            area.spaces.active.region_3d.view_rotation = camera.rotation_euler.to_quaternion()
bpy.ops.wm.save_as_mainfile(filepath=blend_path)
print(json.dumps({'saved':bpy.data.filepath,'active_scene':scene.name,'exported_objects':len(selected),
 'export_result':sorted(result),'converted_curves_and_labels':converted_count,'review_scene':review.name,'parent_positions':{fid:list(bpy.data.objects[fid].matrix_world.translation) for fid in PARENTS}},ensure_ascii=False))
