"""Run in live Blender; GRAPH is injected from the saved candidate contract."""
import bpy
import json
import math
from mathutils import Vector

GRAPH = None  # replaced with json.loads(...) by the caller
BASE='/path/to/wulanchabu-energy-map'
assert GRAPH is not None
assert bpy.data.filepath.endswith('/m11-integrated-v1/乌兰察布_整合场景_v1.blend')
assert not bpy.data.is_dirty, 'Protect unsaved user edits before building'
assert bpy.data.collections.get('M12 | 候选端口与连接') is None
bpy.ops.wm.save_as_mainfile(filepath=BASE+'/'+GRAPH['blender_source'])
scene=bpy.data.scenes['06 | 全区整合交互']
bpy.context.window.scene=scene
collection=bpy.data.collections.new('M12 | 候选端口与连接')
scene.collection.children.link(collection)

def material(name,color):
    mat=bpy.data.materials.new('M12 | '+name)
    mat.use_nodes=True
    shader=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    shader.inputs['Base Color'].default_value=(*color,1)
    shader.inputs['Metallic'].default_value=.25
    shader.inputs['Roughness'].default_value=.38
    mat.diffuse_color=(*color,1)
    return mat

mats={k:material(k,c) for k,c in {'supply':(.95,.35,.11),'return':(.15,.52,.88),
    'CO2':(.64,.34,.9),'electricity':(.95,.72,.12),'signal':(.12,.7,.6),'collar':(.72,.76,.8)}.items()}
def common(obj,owner):
    obj['object_id']=owner.get('object_id',owner.get('asset_id',owner.name))
    obj['revision']=GRAPH['revision']
    obj['status']='candidate_unverified'
    obj['execution_allowed']=False

def tube(name,points,radius,mat,owner):
    data=bpy.data.curves.new(name,'CURVE');data.dimensions='3D';data.resolution_u=1
    data.bevel_depth=radius;data.bevel_resolution=2
    spline=data.splines.new('POLY');spline.points.add(len(points)-1)
    for point,xyz in zip(spline.points,points):point.co=(*xyz,1)
    obj=bpy.data.objects.new(name,data);collection.objects.link(obj);obj.parent=owner
    data.materials.append(mat);common(obj,owner)
    return obj

# The reviewed contract includes this return valve; M10 omitted its geometry.
entry=next(o for o in GRAPH['objects'] if o['object_id']=='STORE_012_DIS_VRETURN')
root=bpy.data.objects.new(entry['object_id'],None);collection.objects.link(root)
root.location=entry['model_root_xyz'];root['object_id']=entry['object_id'];root['parent_id']=entry['parent_id']
root['model_revision']=GRAPH['revision'];root['installation_status']=entry['installation_status']
original=bpy.data.objects['STORE_012_CHARGE_VRETURN | model']
clone=original.copy();clone.data=original.data.copy();clone.name='STORE_012_DIS_VRETURN | model'
collection.objects.link(clone);clone.parent=root;clone.location=original.location;common(clone,root)

# Supersede the old unbound schematic curves in this copy only.
legacy=[]
for obj in bpy.data.collections['M10 | 系统设备补模'].objects:
    if obj.type in {'CURVE','FONT'}:
        obj.hide_render=True;obj.hide_set(True);obj['superseded_by']=GRAPH['revision'];legacy.append(obj.name)

port_objects={}
for port in GRAPH['ports']:
    owner=bpy.data.objects[port['object_id']]
    obj=bpy.data.objects.new('M12_PORT | '+port['port_id'],None)
    collection.objects.link(obj);obj.parent=owner;obj.location=port['position']['xyz_m']
    obj.empty_display_size=1.1;common(obj,owner)
    for key in ['port_id','circuit_id','medium','direction']:obj[key]=port[key]
    obj['position_status']='candidate_model_socket_not_field_nozzle'
    port_objects[port['port_id']]=obj
    # A visible socket collar, separate from the semantic empty port.
    center=Vector(port['position']['xyz_m'])
    ring=[center+Vector((0,math.cos(i*math.tau/16)*.95,math.sin(i*math.tau/16)*.95)) for i in range(17)]
    collar=tube('M12_SOCKET | '+port['port_id'],ring,.18,mats['collar'],owner)
    collar['socket_for']=port['port_id']

bpy.context.view_layer.update()
endpoint_errors=[]
for i,edge in enumerate(GRAPH['connections']):
    a=port_objects[edge['from_port_id']].matrix_world.translation.copy()
    b=port_objects[edge['to_port_id']].matrix_world.translation.copy()
    ids=[edge['from_object_id'],edge['to_object_id']]
    if any(oid.startswith('DRY_019') for oid in ids): owner=bpy.data.objects['M10_C2_SYSTEM']
    elif any(oid.startswith('BOILER_') or oid.startswith('GREEN_POWER') for oid in ids):owner=bpy.data.objects['BOILER_CAND_001']
    elif any(oid.startswith('STORE_') for oid in ids):owner=bpy.data.objects['M10_PTES_SYSTEM']
    else:owner=bpy.data.objects['HUB_011_ROLE_MAPPING']
    internal=edge['role']=='internal'
    level=max(a.z,b.z)+(2 if internal else 8+(i%5)*2)
    lane=(i%3-1)*2
    points=[a,Vector((a.x,a.y,level)),Vector((a.x+lane,b.y,level)),Vector((b.x,b.y,level)),b]
    inverse=owner.matrix_world.inverted()
    local=[inverse@p for p in points]
    key='CO2' if edge['medium']=='co2' else edge['medium'] if edge['medium'] in mats else 'return' if edge['role']=='return' else 'supply'
    radius=.32 if edge['medium'] in {'signal','electricity'} else .6 if internal else 1.1
    obj=tube('M12_EDGE | '+edge['connection_id'],local,radius,mats[key],owner)
    for key in ['connection_id','from_port_id','to_port_id','circuit_id','medium','role']:obj[key]=edge[key]
    obj['model_status']='schematic_connected';obj['branch']=edge.get('branch') or ''
    bpy.context.view_layer.update()
    endpoints=[obj.matrix_world@Vector(obj.data.splines[0].points[j].co[:3]) for j in [0,-1]]
    endpoint_errors.extend([(endpoints[0]-a).length,(endpoints[1]-b).length])
assert max(endpoint_errors)<.002
for entry in GRAPH['objects']:
    bpy.data.objects[entry['object_id']]['model_revision']=GRAPH['revision']
scene['M12_status']='Candidate model sockets and curves only; field hydraulics unverified'
scene['M12_ports']=len(port_objects);scene['M12_connections']=len(GRAPH['connections'])
bpy.ops.wm.save_as_mainfile(filepath=BASE+'/'+GRAPH['blender_source'])
print(json.dumps({'file':bpy.data.filepath,'ports':len(port_objects),'connections':len(GRAPH['connections']),
    'superseded_curves_and_labels':legacy,'max_endpoint_error_m':max(endpoint_errors)},ensure_ascii=False))
