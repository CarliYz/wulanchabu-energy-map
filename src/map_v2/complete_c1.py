"""Build C1's schematic equipment in the live Blender; no filesystem access.

Only objects bearing m8_revision are replaced on rerun. The saved pre-change
checkpoint preserves the three superseded opaque station/terminal objects.
"""
import bpy
import json
import math
from mathutils import Vector

REV = 'c1-dual-loop-v1'
root = bpy.data.objects['AGRI_018']
assert root.get('connection_status') == 'future_candidate_not_P1_connected'
collection = bpy.data.collections.get('M8 | C1 双回路与控制')
if collection is None:
    collection = bpy.data.collections.new('M8 | C1 双回路与控制')
    bpy.data.collections['MAP_V2'].children.link(collection)
for obj in list(collection.objects):
    assert obj.get('m8_revision') == REV, ('unexpected object', obj.name)
    # Greenhouse legacy children must survive replacing their logical container.
    for child in list(obj.children):
        if child.get('m8_revision') != REV:
            matrix = child.matrix_world.copy()
            child.parent = root
            child.matrix_world = matrix
    bpy.data.objects.remove(obj, do_unlink=True)


def material(name, color, metallic=0.0):
    m = bpy.data.materials.get('M8 | ' + name)
    if m is None:
        m = bpy.data.materials.new('M8 | ' + name)
    m.use_nodes = True
    m.diffuse_color = (*color, 1)
    p = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Metallic'].default_value = metallic
    p.inputs['Roughness'].default_value = .4
    return m


red = material('热水供', (.89, .20, .09), .35)
blue = material('热水回', (.08, .36, .84), .35)
green = material('营养供', (.12, .62, .29), .15)
teal = material('营养回', (.02, .39, .37), .15)
steel = material('不锈钢', (.66, .73, .77), .75)
white = material('设备白', (.84, .87, .85), .1)
black = material('控制屏', (.035, .07, .10))
gold = material('控制信号', (.96, .65, .12), .1)
primary = material('一次侧预留', (.57, .36, .75), .2)
entities = {}
port_objects = {}
edge_objects = []


def common(obj, object_id, circuit=None):
    obj['m8_revision'] = REV
    obj['object_id'] = object_id
    obj['parent_id'] = 'AGRI_018'
    obj['installation_status'] = 'candidate_unverified'
    obj['model_status'] = 'schematic_built'
    if circuit:
        obj['circuit_id'] = circuit
    return obj


def entity(suffix, title, origin):
    oid = 'AGRI_018_' + suffix
    o = bpy.data.objects.new(oid, None)
    collection.objects.link(o)
    o.parent = root
    o.location = origin
    o.empty_display_size = 1
    o['label'] = title
    common(o, oid)
    entities[oid] = o
    return o


def local_point(p, owner):
    return Vector(p) - owner.location if owner != root else Vector(p)


def mesh(name, vertices, faces, mat, owner):
    d = bpy.data.meshes.new('M8 | ' + name)
    d.from_pydata([tuple(local_point(p, owner)) for p in vertices], [], faces)
    d.update()
    o = bpy.data.objects.new('M8 | ' + name, d)
    collection.objects.link(o)
    o.parent = owner
    d.materials.append(mat)
    common(o, owner.get('object_id', 'AGRI_018'))
    return o


def box(name, center, size, mat, owner):
    c = Vector(center)
    vs = [tuple(c + Vector((dx*size[0]/2, dy*size[1]/2, dz*size[2]/2)))
          for dx,dy,dz in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),
                           (-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
    return mesh(name, vs, [(0,3,2,1),(4,5,6,7),(0,1,5,4),
                           (1,2,6,5),(2,3,7,6),(3,0,4,7)], mat, owner)


def cylinder(name, a, b, radius, mat, owner, sides=16):
    a, b = Vector(a), Vector(b)
    axis = (b-a).normalized()
    u = axis.cross(Vector((0,0,1)))
    if u.length < .01:
        u = axis.cross(Vector((1,0,0)))
    u.normalize()
    v = axis.cross(u).normalized()
    vs = [tuple(c + radius*(math.cos(i*2*math.pi/sides)*u + math.sin(i*2*math.pi/sides)*v))
          for c in (a,b) for i in range(sides)]
    fs = [tuple(range(sides-1,-1,-1)),tuple(range(sides,2*sides))]
    fs.extend((i,(i+1)%sides,(i+1)%sides+sides,i+sides) for i in range(sides))
    return mesh(name, vs, fs, mat, owner)


def pipe(name, points, radius, mat, owner=root, circuit=None):
    d = bpy.data.curves.new('M8 | ' + name, 'CURVE')
    d.dimensions = '3D'
    d.resolution_u = 1
    d.bevel_depth = radius
    d.bevel_resolution = 2
    s = d.splines.new('POLY')
    s.points.add(len(points)-1)
    for p, xyz in zip(s.points, points):
        p.co = (*local_point(xyz, owner), 1)
    o = bpy.data.objects.new('M8 | ' + name, d)
    collection.objects.link(o)
    o.parent = owner
    d.materials.append(mat)
    common(o, owner.get('object_id', 'AGRI_018'), circuit)
    o['display_radius_is_engineering_dimension'] = False
    return o


def label(body, xyz, owner=root, size=1.5):
    d = bpy.data.curves.new('M8 | 标签', 'FONT')
    d.body = body
    d.size = size
    font = bpy.data.fonts.get('STHeiti Medium')
    if font:
        d.font = font
    o = bpy.data.objects.new('M8 | ' + body, d)
    collection.objects.link(o)
    o.parent = owner
    o.location = local_point(xyz, owner)
    d.materials.append(black)
    common(o, owner.get('object_id', 'AGRI_018'))
    return o


def port(owner, circuit, direction, role, xyz, medium):
    pid = owner['object_id'] + ':' + circuit + ':' + direction + ':' + role
    assert pid not in port_objects
    o = bpy.data.objects.new('M8_PORT_%02d' % len(port_objects), None)
    collection.objects.link(o)
    o.parent = owner
    o.location = local_point(xyz, owner)
    o.empty_display_size = .45
    common(o, owner['object_id'], circuit)
    o['port_id'], o['direction'], o['medium'] = pid, direction, medium
    port_objects[pid] = o
    return pid


def edge(number, from_pid, to_pid, middle=()):
    a, b = port_objects[from_pid], port_objects[to_pid]
    assert a['circuit_id'] == b['circuit_id'] and a['medium'] == b['medium']
    assert a['direction'] == 'out' and b['direction'] == 'in'
    # World matrices have not yet been evaluated; positions are C1-local.
    pa, pb = a.parent.location+a.location, b.parent.location+b.location
    c = a['circuit_id']
    mat = gold if c == 'C1_CONTROL' else (green if c == 'C1_NUTRIENT' else red)
    if 'return' in from_pid or (c == 'C1_HEAT' and number == 17):
        mat = blue if c == 'C1_HEAT' else teal
    if c == 'C1_NUTRIENT' and number == 24:
        mat = teal
    o = pipe('EDGE_%03d' % number, [tuple(pa), *middle, tuple(pb)],
             .07 if c == 'C1_CONTROL' else .20, mat, circuit=c)
    o['connection_id'] = 'EDGE_%03d' % number
    o['from_port_id'], o['to_port_id'] = from_pid, to_pid
    o['design_status'] = 'proposed'
    edge_objects.append(o)


hx = entity('HX', '隔离板换：仅传热不混水', (-84,-60,0))
pump = entity('PUMP', '二次热水循环泵', (-66,-58,0))
valve = entity('VALVE', '调节阀与隔离阀', (-54,-58,0))
header = entity('HEADER', '热水供回分集水器', (-15,-49,0))
gh1 = entity('GH1', '第一组温室', (-47,10,0))
gh2 = entity('GH2', '第二组温室', (20,10,0))
tank = entity('TANK', '营养液箱', (27,-62,0))
npump = entity('NPUMP', '营养液专用循环泵', (38,-64,0))
nheader = entity('NHEADER', '营养液分配回收集管', (-15,-44,0))
sensor = entity('SENSOR', '温度/流量测点', (-61,-48,0))
ctrl = entity('CTRL', 'PLC控制柜', (64,-62,0))

# Preserve old geometry in the checkpoint; hide only explicitly superseded parts.
for name in ['AGRI_018 用户隔离换热站','AGRI_018 末端供水','AGRI_018 末端回水']:
    o = bpy.data.objects[name]
    o.hide_render = True
    o.hide_viewport = True
    o['superseded_by'] = REV

box('板换底座',(-84,-60,.25),(10,9,.5),white,hx)
for i in range(14):
    box('板式换热片 %02d'%i,(-85.8+i*.27,-60,2.6),(.12,4.8,4.1),steel,hx)
for x in (-86.2,-81.8):
    box('板换端板',(x,-60,2.6),(.25,5.2,4.6),primary,hx)
for y in (-62.3,-57.7):
    for z in (.7,4.5):
        cylinder('板换拉杆',(-86.8,y,z),(-81.4,y,z),.10,steel,hx)
label('一次侧预留 / 隔离板换',(-90,-68,.7),size=1.3)
pin = port(hx,'USER','in','flow',(-91,-58,3),'water')
pout = port(hx,'USER','out','flow',(-91,-62,3),'water')
pipe('一次侧供接口',[(-91,-58,3),(-86.3,-58,3)],.25,primary,hx,'USER')
pipe('一次侧回接口',[(-86.3,-62,3),(-91,-62,3)],.25,primary,hx,'USER')
hxo = port(hx,'C1_HEAT','out','flow',(-81.7,-58,3),'water')
hxi = port(hx,'C1_HEAT','in','flow',(-81.7,-62,2),'water')


def pump_body(owner, x, y, mat):
    box('泵底座',(x,y,.25),(5,3,.5),white,owner)
    cylinder('蜗壳',(x-.8,y,1.4),(x+.8,y,1.4),1.05,mat,owner)
    cylinder('电机',(x,y+1,1.4),(x,y+3,1.4),.7,steel,owner)
    for yy in (y+1.2,y+1.55,y+1.9,y+2.25,y+2.6):
        cylinder('电机散热环',(x,yy,1.4),(x,yy+.10,1.4),.77,steel,owner)
    for xx in (x-2,x+2):
        cylinder('泵接口法兰',(xx-.12,y,1.4),(xx+.12,y,1.4),.45,steel,owner)


pump_body(pump,-66,-58,red)
pi = port(pump,'C1_HEAT','in','flow',(-68,-58,1.4),'water')
po = port(pump,'C1_HEAT','out','flow',(-64,-58,1.4),'water')
pipe('泵内部流道',[(-68,-58,1.4),(-64,-58,1.4)],.23,red,pump,'C1_HEAT')
box('调节阀本体',(-54,-58,1.4),(2,1.7,1.7),steel,valve)
box('电动执行器',(-54,-58,3.2),(2,1.8,1.1),gold,valve)
cylinder('执行器阀杆',(-54,-58,2.1),(-54,-58,2.7),.15,steel,valve)
vi = port(valve,'C1_HEAT','in','flow',(-56,-58,1.4),'water')
vo = port(valve,'C1_HEAT','out','flow',(-52,-58,1.4),'water')
pipe('阀内部流道',[(-56,-58,1.4),(-52,-58,1.4)],.22,red,valve,'C1_HEAT')
for x in (-57.5,-50.5):
    cylinder('隔离阀阀杆',(x,-58,1.4),(x,-58,2.3),.13,steel,valve)
    cylinder('隔离阀手轮',(x,-58,2.3),(x,-58,2.5),.6,red,valve)

hi = port(header,'C1_HEAT','in','flow',(-48,-48,1.4),'water')
ho = port(header,'C1_HEAT','out','flow',(-76,-51,.65),'water')
pipe('热水供集管',[(-76,-48,1.4),(45,-48,1.4)],.27,red,header,'C1_HEAT')
pipe('热水回集管',[(-76,-51,.65),(45,-51,.65)],.27,blue,header,'C1_HEAT')
edge(14,hxo,pi,[(-78,-58,3),(-78,-58,1.4)])
edge(15,po,vi)
edge(16,vo,hi,[(-48,-58,1.4)])
edge(17,ho,hxi,[(-78,-51,.65),(-78,-62,.65),(-78,-62,2)])

# Logical greenhouse IDs own the existing detailed shells and channels.
bpy.context.view_layer.update()
for o in list(root.children):
    if o.get('m8_revision') == REV or not any(o.name.startswith(t) for t in
        ['温室','leaf |','水培槽','叶菜苗盘']):
        continue
    if o.type not in {'MESH','CURVE'}:
        continue
    center = sum((root.matrix_world.inverted() @ (o.matrix_world @ Vector(p))
                  for p in o.bound_box), Vector())/8
    owner = gh1 if center.x < -10 else gh2
    mw = o.matrix_world.copy()
    o.parent = owner
    o.matrix_world = mw
    o['object_id'] = owner['object_id']
    o['circuit_owner'] = 'C1_HEAT' if '温室供水' in o.name or '温室回水' in o.name else 'C1_NUTRIENT' if o.name.startswith('水培槽') else 'structure'

for idx,(gh,cx) in enumerate([(gh1,-47),(gh2,20)]):
    inlet_x = cx-24.5
    role_s = gh['object_id']+'_supply'
    role_r = gh['object_id']+'_return'
    hs = port(header,'C1_HEAT','out',role_s,(inlet_x,-48,1.4),'water')
    gs = port(gh,'C1_HEAT','in',role_s,(inlet_x,-40,1),'water')
    gr = port(gh,'C1_HEAT','out',role_r,(inlet_x,-41.5,1),'water')
    hr = port(header,'C1_HEAT','in',role_r,(inlet_x,-51,.65),'water')
    edge(18+idx*2,hs,gs)
    edge(19+idx*2,gr,hr,[(inlet_x,-44,.65)])
    # Five representative heating loops, attached to the old supply/return headers.
    for j in range(5):
        x=cx-22+j*9
        pipe('GH%d 散热支路%d'%(idx+1,j+1),[(x,-40,1),(x,-37,.45),(x,55,.45),
            (x+1,55,.45),(x+1,-41.5,.25),(x+1,-41.5,1)],.13,red,gh,'C1_HEAT')
    label('温室 %d · 热水 / 营养液独立'%(idx+1),(cx-20,61,.4),size=1.4)

box('营养液箱',(27,-62,2.2),(6,5,4.4),white,tank)
box('营养液箱顶盖',(27,-62,4.5),(6.2,5.2,.2),green,tank)
box('液位窗',(27,-64.53,2.4),(1,.07,3),teal,tank)
box('pH EC 仪表',(27,-64.7,3.2),(2,.25,1),black,tank)
to = port(tank,'C1_NUTRIENT','out','flow',(30,-64,1.4),'nutrient')
ti = port(tank,'C1_NUTRIENT','in','flow',(30,-61,2),'nutrient')
pump_body(npump,38,-64,green)
ni = port(npump,'C1_NUTRIENT','in','flow',(36,-64,1.4),'nutrient')
no = port(npump,'C1_NUTRIENT','out','flow',(40,-64,1.4),'nutrient')
pipe('营养液泵流道',[(36,-64,1.4),(40,-64,1.4)],.2,green,npump,'C1_NUTRIENT')
nhi = port(nheader,'C1_NUTRIENT','in','flow',(44,-44,1.9),'nutrient')
nho = port(nheader,'C1_NUTRIENT','out','flow',(49,64,.45),'nutrient')
pipe('营养供液总管',[(-72,-44,1.9),(44,-44,1.9)],.19,green,nheader,'C1_NUTRIENT')
pipe('营养回收总管',[(-72,64,.45),(49,64,.45)],.19,teal,nheader,'C1_NUTRIENT')
edge(22,to,ni)
edge(23,no,nhi,[(44,-64,1.4),(44,-44,1.4)])
edge(24,nho,ti,[(49,-61,.45),(49,-61,2)])
for idx,(gh,cx) in enumerate([(gh1,-47),(gh2,20)]):
    x=cx-20.3
    rs,rr=gh['object_id']+'_supply',gh['object_id']+'_return'
    ns=port(nheader,'C1_NUTRIENT','out',rs,(x,-44,1.9),'nutrient')
    gi=port(gh,'C1_NUTRIENT','in',rs,(x,-37.5,1),'nutrient')
    go=port(gh,'C1_NUTRIENT','out',rr,(x,57.5,1),'nutrient')
    nr=port(nheader,'C1_NUTRIENT','in',rr,(x,64,.45),'nutrient')
    edge(25+idx*2,ns,gi,[(x,-39,1.9)])
    edge(26+idx*2,go,nr)
    pipe('GH%d 供液分配'%(idx+1),[(x,-37.5,1),(x+40.5,-37.5,1)],.14,green,gh,'C1_NUTRIENT')
    pipe('GH%d 回液收集'%(idx+1),[(x,57.5,1),(x+40.5,57.5,1)],.14,teal,gh,'C1_NUTRIENT')
    for j in range(10):
        xx=x+j*4.5
        pipe('GH%d 水培槽循环%d'%(idx+1,j+1),[(xx,-37.5,1),(xx,-36,1.15),
            (xx,56,1.15),(xx,57.5,1)],.08,green,gh,'C1_NUTRIENT')

box('PLC 控制柜',(64,-62,2.4),(4,2.5,4.8),white,ctrl)
box('PLC 屏幕',(64,-63.3,3.2),(2.5,.12,1.4),black,ctrl)
label('PLC · 温度 / 流量 / pH / EC 待核',(54,-69,.4),size=1.2)
for x,y,z in [(-61,-48,1.4),(-61,-51,.65)]:
    cylinder('温度传感探杆',(x,y,z),(x,y,z+1.1),.12,steel,sensor)
    box('温度测点',(x,y,z+1.3),(1,.8,.5),gold,sensor)
cylinder('流量计',(-59,-48,1.4),(-57,-48,1.4),.45,steel,sensor)
sp=port(sensor,'C1_CONTROL','out','measurement',(-61,-48,2.7),'signal')
ci=port(ctrl,'C1_CONTROL','in','measurement',(62,-62,3.4),'signal')
co=port(ctrl,'C1_CONTROL','out','command',(66,-62,3.4),'signal')
pc=port(pump,'C1_CONTROL','in','command',(-66,-55,1.4),'signal')
vc=port(valve,'C1_CONTROL','in','command',(-54,-58,3.7),'signal')
nc=port(npump,'C1_CONTROL','in','command',(38,-61,1.4),'signal')
edge(29,sp,ci,[(-61,-53,.25),(60,-53,.25),(60,-62,3.4)])
edge(30,co,pc,[(69,-62,.25),(69,-70,.25),(-66,-70,.25),(-66,-55,.25)])
edge(31,co,vc,[(69,-62,.25),(69,-71,.25),(-54,-71,.25),(-54,-58,.25)])
edge(32,co,nc,[(69,-62,.25),(69,-72,.25),(38,-72,.25),(38,-61,.25)])
label('红/蓝：温控热水   绿/青：营养液   金：控制信号',(-72,-74,.5),size=1.6)
root['m8_revision'] = REV
root['model_status'] = 'schematic_built_pending_independent_audit'
root['external_interface_status'] = 'reserved_not_operating'
root['engineering_sizing_status'] = 'not_verified'
bpy.context.view_layer.update()
print(json.dumps({'revision':REV,'entities':len(entities),'ports':len(port_objects),
                  'connections':len(edge_objects),'external_status':root['connection_status'],
                  'child_count':len(root.children_recursive)},ensure_ascii=False))
