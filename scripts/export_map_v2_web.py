"""Export the saved Blender geographic model for the browser viewer."""
import os
import bpy

ROOT = '/path/to/wulanchabu-energy-map'
OUTPUT = os.path.join(ROOT, 'web', 'map-viewer', 'assets', '乌兰察布_真实地理场景_v2.glb')
EXCLUDED_COLLECTIONS = {
    '07 地理相机',
    '08 总览标签',
    '09 总览管线强调 | 非真实管径',
}

os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
map_collection = bpy.data.collections['MAP_V2']
bpy.ops.object.select_all(action='DESELECT')
selected = []
for obj in map_collection.all_objects:
    if obj.type not in {'MESH', 'CURVE', 'SURFACE', 'META', 'FONT'}:
        continue
    if any(collection.name in EXCLUDED_COLLECTIONS for collection in obj.users_collection):
        continue
    obj.select_set(True)
    selected.append(obj)

if not selected:
    raise RuntimeError('MAP_V2 has no exportable geometry')

bpy.context.view_layer.objects.active = selected[0]
bpy.ops.export_scene.gltf(
    filepath=OUTPUT,
    export_format='GLB',
    use_selection=True,
    export_apply=True,
    export_texcoords=True,
    export_normals=True,
    export_materials='EXPORT',
    export_cameras=False,
    export_lights=False,
)

print({'out': OUTPUT, 'objects': len(selected), 'bytes': os.path.getsize(OUTPUT)})
