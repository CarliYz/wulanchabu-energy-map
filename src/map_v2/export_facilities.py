"""Run in live Blender: export the twelve semantic facility roots without changing sources."""
import bpy
import json

BASE = '/path/to/wulanchabu-energy-map'
OUT = BASE + '/web/map-viewer/assets/facilities-v1'
IDS = ['DC_004', 'DC_005', 'DC_006', 'HUB_011', 'STORE_012', 'DEMO_013',
       'AGRI_014', 'AGRI_015', 'AGRI_016', 'AGRI_017', 'AGRI_018', 'DRY_019']
assert not bpy.data.is_dirty, 'Save/reconcile user edits before exporting'
source = bpy.data.filepath
scene = bpy.context.scene
selection = list(bpy.context.selected_objects)
active = bpy.context.view_layer.objects.active
receipt = {'revision': 'facilities-semantic-v1', 'source_blend': str(source),
           'objects': []}
try:
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for fid in IDS:
        root = bpy.data.objects[fid]
        assert root.get('asset_id') == fid and root.name in scene.objects
        included = [root] + [o for o in root.children_recursive
                            if not o.hide_render and not o.get('superseded_by')]
        for o in included:
            o.select_set(True)
        slab = bpy.data.objects[fid + ' | 场坪']
        props = {}
        for k, v in root.items():
            props[k] = list(v) if hasattr(v, 'to_list') else v
        receipt['objects'].append({'object_id': fid, 'root_xyz': list(root.matrix_world.translation),
                                   'included_objects': len(included), 'names': [o.name for o in included],
                                   'model_footprint_m2': round(slab.dimensions.x * slab.dimensions.y, 2),
                                   'properties': props})
    bpy.context.view_layer.objects.active = bpy.data.objects['HUB_011']
    result = bpy.ops.export_scene.gltf(filepath=OUT + '/facilities.glb', export_format='GLB',
        use_selection=True, use_active_scene=True, export_apply=True, export_extras=True,
        export_cameras=False, export_lights=False)
    assert 'FINISHED' in result
finally:
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in selection:
        o.select_set(True)
    bpy.context.view_layer.objects.active = active
print(json.dumps(receipt, ensure_ascii=False))
