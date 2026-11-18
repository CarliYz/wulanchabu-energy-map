"""Add four agricultural instrument proxies in a new live Blender copy."""
import bpy
import math
import json
from mathutils import Vector

BASE = '/path/to/wulanchabu-energy-map'
OUT = BASE + '/outputs/m14-agriculture-sensors-v1'
IDS = ['AGRI_014_SENSOR', 'AGRI_015_SENSOR', 'AGRI_016_SENSOR', 'AGRI_017_SENSOR']
scene = bpy.data.scenes['06 | 全区整合交互']
assert bpy.data.filepath.endswith('/m12-connected-v1/乌兰察布_连接整合场景_v1.blend')
assert bpy.data.collections.get('M14 | 农业测点实体示意') is None
before = {o.name: tuple(v for row in o.matrix_world for v in row) for o in bpy.data.objects}
roots = {i: bpy.data.objects[i] for i in IDS}
assert all(o.type == 'EMPTY' and not o.children for o in roots.values())
source = bpy.data.filepath
source_dirty = bpy.data.is_dirty
bpy.ops.wm.save_as_mainfile(filepath=OUT + '/乌兰察布_农业测点补模_v1.blend')
bpy.context.window.scene = scene
collection = bpy.data.collections.new('M14 | 农业测点实体示意')
scene.collection.children.link(collection)

def material(name, color, metallic=0):
    mat = bpy.data.materials.new('M14 | ' + name)
    mat.use_nodes = True
    mat.diffuse_color = (*color, 1)
    bsdf = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Metallic'].default_value = metallic
    bsdf.inputs['Roughness'].default_value = .35
    return mat

steel = material('仪表不锈钢', (.55, .62, .68), .7)
blue = material('变送器蓝', (.06, .28, .45), .35)
black = material('空白显示屏', (.012, .022, .032), .1)
amber = material('样件端盖', (.95, .48, .06), .1)
base_mat = material('支座石墨灰', (.16, .2, .24), .3)

def mesh(owner, name, vertices, faces, mat):
    data = bpy.data.meshes.new('M14 | ' + owner.name + ' | ' + name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(data.name, data)
    collection.objects.link(obj)
    obj.parent = owner
    obj['object_id'] = owner['object_id']
    obj['model_revision'] = 'm14-agriculture-sensors-v1'
    obj['model_status'] = 'schematic_proxy_unconnected'
    obj['installation_status'] = 'candidate_unverified'
    data.materials.append(mat)
    return obj

def box(owner, name, center, size, mat):
    c = Vector(center)
    vertices = [tuple(c + Vector((x*size[0]/2,y*size[1]/2,z*size[2]/2)))
        for x,y,z in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),
                      (-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
    return mesh(owner,name,vertices,[(0,3,2,1),(4,5,6,7),(0,1,5,4),
        (1,2,6,5),(2,3,7,6),(3,0,4,7)],mat)

def cylinder(owner, name, a, b, radius, mat, sides=24):
    a,b = Vector(a),Vector(b)
    axis=(b-a).normalized()
    u=axis.cross(Vector((0,0,1)))
    if u.length < .01:
        u=axis.cross(Vector((1,0,0)))
    u.normalize()
    v=axis.cross(u).normalized()
    vertices=[tuple(c+radius*(math.cos(k*2*math.pi/sides)*u+math.sin(k*2*math.pi/sides)*v))
        for c in (a,b) for k in range(sides)]
    faces=[tuple(range(sides-1,-1,-1)),tuple(range(sides,2*sides))]
    faces.extend((k,(k+1)%sides,(k+1)%sides+sides,k+sides) for k in range(sides))
    return mesh(owner,name,vertices,faces,mat)

for oid, owner in roots.items():
    box(owner,'支座',(0,0,-1.9),(4.9,1.9,.2),base_mat)
    for x in [-1.1,1.1]:
        box(owner,'支腿',(x,0,-1.1),(.2,.9,1.4),steel)
        box(owner,'管夹横托',(x,0,-.57),(.6,1.1,.18),steel)
    cylinder(owner,'流量计测量样管',(-2,0,-.25),(2,0,-.25),.32,steel)
    for x in [-1.7,-.6,.6,1.7]:
        cylinder(owner,'法兰',(x-.08,0,-.25),(x+.08,0,-.25),.52,steel)
        for angle in [math.pi/4,3*math.pi/4,5*math.pi/4,7*math.pi/4]:
            y=.43*math.cos(angle)
            z=-.25+.43*math.sin(angle)
            cylinder(owner,'法兰螺栓',(x-.12,y,z),(x+.12,y,z),.06,base_mat,8)
    for x in [-2.06,2.06]:
        cylinder(owner,'未接管样件端盖',(x-.05,0,-.25),(x+.05,0,-.25),.37,amber)
    cylinder(owner,'流量变送器支颈',(0,0,.02),(0,0,.62),.16,steel)
    box(owner,'流量变送器壳体',(0,0,1),(1.22,.74,1.05),blue)
    box(owner,'流量仪表空屏',(0,-.381,1.04),(.85,.025,.57),black)
    for x in [-.28,0,.28]:
        cylinder(owner,'仪表按键',(x,-.39,.67),(x,-.43,.67),.055,steel,12)
    cylinder(owner,'温度探杆',(-1.15,0,-.22),(-1.15,0,1.35),.065,steel)
    box(owner,'温度变送器',(-1.15,0,1.45),(.55,.42,.42),blue)
    box(owner,'温度仪表空屏',(-1.15,-.216,1.45),(.33,.02,.2),black)
    owner['model_revision']='m14-agriculture-sensors-v1'
    owner['model_status']='schematic_proxy_unconnected'
    owner['engineering_limits']='Display-scale sample only; manufacturer, range, pipe taps, control signals and field placement unverified'
    owner['real_measurements_available']=False
bpy.context.view_layer.update()
unchanged = all(before[n] == tuple(v for row in bpy.data.objects[n].matrix_world for v in row) for n in before)
assert unchanged, 'Original object transform changed'
for obj in scene.objects:
    obj.select_set(obj in roots.values() or obj.name in collection.objects)
bpy.context.view_layer.objects.active=roots['AGRI_016_SENSOR']
export=bpy.ops.export_scene.gltf(filepath=OUT+'/four-agriculture-sensors.glb',
    export_format='GLB',use_selection=True,use_active_scene=True,export_apply=True,
    export_extras=True,export_cameras=False,export_lights=False)
assert 'FINISHED' in export
target=roots['AGRI_016_SENSOR'].matrix_world.translation
direction=Vector((5,-8,5))
rotation=(-direction).to_track_quat('-Z','Y')
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            region=area.spaces.active.region_3d
            region.view_perspective=next(i.identifier for i in bpy.types.RegionView3D.bl_rna.properties['view_perspective'].enum_items if i.identifier=='PERSP')
            region.view_location=target
            region.view_distance=11
            region.view_rotation=rotation
            area.spaces.active.shading.type=next(i.identifier for i in bpy.types.View3DShading.bl_rna.properties['type'].enum_items if i.identifier=='MATERIAL')
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print(json.dumps({'status':'modeled_standalone_not_web_integrated','source':source,
    'source_was_dirty':source_dirty,'saved':bpy.data.filepath,'scene':scene.name,
    'original_transforms_unchanged':unchanged,'original_objects_checked':len(before),
    'sensors':{i:{'mesh_children':sum(c.type=='MESH' for c in o.children_recursive),
        'parent':o.parent.get('object_id',o.parent.get('asset_id',o.parent.name)),'matrix_world':list(before[o.name])} for i,o in roots.items()},
    'glb':OUT+'/four-agriculture-sensors.glb',
    'limits':'Unconnected sample instruments at existing schematic roots; no vendor, ranges, measured values or field installation claim'},ensure_ascii=False))
