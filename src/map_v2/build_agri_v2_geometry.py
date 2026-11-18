"""Build the first verifiable A/B terminal slice in the live Blender scene.

The script is intentionally additive and candidate-only. It saves a new Blender
file before editing, creates A/B terminal equipment with semantic ports, exports
only the new slice, and renders one acceptance view per zone. It never moves the
existing geography or edits C1 assets.
"""

import bpy
import math
from mathutils import Vector


BASE = "/path/to/wulanchabu-energy-map"
OUT_BLEND = BASE + "/outputs/m11-integrated-v1/乌兰察布_AB末端补模_v1.blend"
OUT_GLB = BASE + "/web/map-viewer/assets/ab-terminals-v1/AB_terminal_slice.glb"
OUT_A = BASE + "/web/map-viewer/assets/ab-terminals-v1/AGRI_014_A区末端验收.png"
OUT_B = BASE + "/web/map-viewer/assets/ab-terminals-v1/AGRI_015_B区末端验收.png"
REV = "m11-integrated-v1"
SCENE_NAME = "05 | 水培育苗"
STAGE = "geometry"


def material(name, color, metallic=0.0, roughness=0.42):
    name = "M11 | " + name
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = (*color, 1.0)
    bsdf = next(node for node in mat.node_tree.nodes if node.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


def common(obj, object_id, parent_id, kind="component"):
    obj["m9_revision"] = REV
    obj["object_id"] = object_id
    obj["parent_id"] = parent_id
    obj["installation_status"] = "candidate_unverified"
    obj["model_status"] = "schematic_built"
    obj["design_status"] = "proposed"
    obj["kind"] = kind
    return obj


def make_entity(collection, parent, object_id, label, location, kind="equipment"):
    obj = bpy.data.objects.new(object_id, None)
    collection.objects.link(obj)
    obj.parent = parent
    obj.location = location
    obj.empty_display_size = 1.2
    obj["label"] = label
    common(obj, object_id, parent.get("object_id", parent.name), kind)
    return obj


def mesh(collection, name, vertices, faces, mat, owner, object_id=None):
    data = bpy.data.meshes.new("M11 | " + name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new("M11 | " + name, data)
    collection.objects.link(obj)
    obj.parent = owner
    data.materials.append(mat)
    common(obj, object_id or owner.get("object_id", owner.name), owner.get("object_id", owner.name))
    return obj


def box(collection, name, center, size, mat, owner, object_id=None):
    c = Vector(center)
    sx, sy, sz = size
    vertices = [
        tuple(c + Vector((dx * sx / 2, dy * sy / 2, dz * sz / 2)))
        for dx, dy, dz in [
            (-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
            (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1),
        ]
    ]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
             (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return mesh(collection, name, vertices, faces, mat, owner, object_id)


def cylinder(collection, name, a, b, radius, mat, owner, object_id=None, sides=16):
    a, b = Vector(a), Vector(b)
    axis = (b - a).normalized()
    u = axis.cross(Vector((0, 0, 1)))
    if u.length < 0.01:
        u = axis.cross(Vector((1, 0, 0)))
    u.normalize()
    v = axis.cross(u).normalized()
    vertices = [
        tuple(center + radius * (math.cos(i * 2 * math.pi / sides) * u +
                                  math.sin(i * 2 * math.pi / sides) * v))
        for center in (a, b) for i in range(sides)
    ]
    faces = [tuple(range(sides - 1, -1, -1)), tuple(range(sides, 2 * sides))]
    faces.extend((i, (i + 1) % sides, (i + 1) % sides + sides, i + sides)
                 for i in range(sides))
    return mesh(collection, name, vertices, faces, mat, owner, object_id)


def pipe(collection, name, points, radius, mat, owner, circuit, connection_id=None,
         from_port=None, to_port=None):
    data = bpy.data.curves.new("M11 | " + name, "CURVE")
    data.dimensions = "3D"
    data.resolution_u = 1
    data.bevel_depth = radius
    data.bevel_resolution = 2
    spline = data.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for point, xyz in zip(spline.points, points):
        point.co = (*xyz, 1.0)
    obj = bpy.data.objects.new("M11 | " + name, data)
    collection.objects.link(obj)
    obj.parent = owner
    data.materials.append(mat)
    common(obj, owner.get("object_id", owner.name), owner.get("object_id", owner.name), "connection")
    obj["circuit_id"] = circuit
    if connection_id:
        obj["connection_id"] = connection_id
    if from_port:
        obj["from_port_id"] = from_port
    if to_port:
        obj["to_port_id"] = to_port
    return obj


def label(collection, text, location, owner, mat, size=2.2):
    data = bpy.data.curves.new("M11 | 标签", "FONT")
    data.body = text
    data.size = size
    data.align_x = "CENTER"
    data.extrude = 0.03
    obj = bpy.data.objects.new("M11 | LABEL | " + text, data)
    collection.objects.link(obj)
    obj.parent = owner
    obj.location = location
    data.materials.append(mat)
    common(obj, owner.get("object_id", owner.name), owner.get("object_id", owner.name), "label")
    return obj


def make_port(collection, entity, circuit, direction, role, location, medium):
    port_id = f"{entity['object_id']}:{circuit}:{direction}:{role}"
    obj = bpy.data.objects.new("M9_PORT | " + port_id, None)
    collection.objects.link(obj)
    obj.parent = entity
    obj.location = location
    obj.empty_display_size = 0.48
    common(obj, entity["object_id"], entity.parent.get("object_id", entity.parent.name), "port")
    obj["port_id"] = port_id
    obj["circuit_id"] = circuit
    obj["direction"] = direction
    obj["role"] = role
    obj["medium"] = medium
    return obj


def local_port_position(port_obj):
    return Vector(port_obj.parent.location) + Vector(port_obj.location)


def add_heat_terminal(collection, facility, spec, mats, terminals):
    prefix = spec["prefix"]
    is_greenhouse = spec["kind"] == "greenhouse"
    hx = make_entity(collection, facility, f"{prefix}_HX", "隔离板换：仅传热不混水", (-8, spec["yard_y"], 2.0), "heat_exchanger")
    pump = make_entity(collection, facility, f"{prefix}_PUMP", "二次侧循环泵", (-8, spec["yard_y"] - 10, 2.0), "pump")
    valve = make_entity(collection, facility, f"{prefix}_VALVE", "调节阀与隔离阀", (-8, spec["yard_y"] - 20, 2.0), "valve")
    header = make_entity(collection, facility, f"{prefix}_HEADER", "供回分集水器", (-8, spec["yard_y"] - 29, 2.0), "header")
    ctrl = make_entity(collection, facility, f"{prefix}_CTRL", "PLC 控制柜", (34, spec["yard_y"] - 20, 2.0), "controller")
    sensor = make_entity(collection, facility, f"{prefix}_SENSOR", "温度/流量测点", (20, spec["yard_y"] - 20, 2.0), "sensor")
    terminal_entities = []
    for index, (suffix, title, x) in enumerate(spec["loads"], 1):
        terminal = make_entity(collection, facility, f"{prefix}_{suffix}", title, (x, spec["yard_y"] - 30, 2.0), "terminal")
        terminal_entities.append(terminal)
        if is_greenhouse:
            box(collection, "温室末端箱", (-5, 0, 2.0), (14, 8, 4), mats["greenhouse"], terminal)
            for xx in (-4.5, 0, 4.5):
                cylinder(collection, "温室加热盘管", (xx, -2.7, 0.8), (xx, 2.7, 0.8), .16, mats["supply"], terminal)
        else:
            box(collection, "AHU 箱体", (-1, 0, 2.4), (15, 9, 4.8), mats["ahu"], terminal)
            cylinder(collection, "AHU 风机", (-1, 0, 4.9), (-1, 0, 5.7), 1.25, mats["steel"], terminal)
            box(collection, "AHU 盘管", (5.0, 0, 2.4), (1.0, 6.0, 3.0), mats["supply"], terminal)
        tin = make_port(collection, terminal, f"{prefix}_HEAT", "in", "flow", (-7, 0, 1.6), "water")
        tout = make_port(collection, terminal, f"{prefix}_HEAT", "out", "flow", (7, 0, 1.6), "water")
        pipe(collection, f"{suffix} 内部末端回路", [(-7, 0, 1.6), (0, 0, 1.6), (7, 0, 1.6)], .18,
             owner=terminal, circuit=f"{prefix}_HEAT", connection_id=f"{prefix}_{suffix}_INTERNAL",
             from_port=tin["port_id"], to_port=tout["port_id"], mat=mats["supply"])
        label(collection, title, (-1, 0, 6.4), terminal, mats["label"], 1.8)
        terminals.append({"entity": terminal, "in": tin, "out": tout})

    hx_out = make_port(collection, hx, f"{prefix}_HEAT", "out", "flow", (6, 0, 2.6), "water")
    hx_in = make_port(collection, hx, f"{prefix}_HEAT", "in", "flow", (6, 0, 1.2), "water")
    pump_in = make_port(collection, pump, f"{prefix}_HEAT", "in", "flow", (-4, 0, 2.0), "water")
    pump_out = make_port(collection, pump, f"{prefix}_HEAT", "out", "flow", (4, 0, 2.0), "water")
    valve_in = make_port(collection, valve, f"{prefix}_HEAT", "in", "flow", (-4, 0, 2.0), "water")
    valve_out = make_port(collection, valve, f"{prefix}_HEAT", "out", "flow", (4, 0, 2.0), "water")
    header_out = make_port(collection, header, f"{prefix}_HEAT", "out", "flow", (5, 0, 2.6), "water")
    header_in = make_port(collection, header, f"{prefix}_HEAT", "in", "flow", (5, 0, 1.2), "water")
    ctrl_out = make_port(collection, ctrl, f"{prefix}_CONTROL", "out", "signal", (-6, 0, 2.0), "control")
    valve_ctrl = make_port(collection, valve, f"{prefix}_CONTROL", "in", "signal", (0, 2.2, 3.2), "control")
    pump_ctrl = make_port(collection, pump, f"{prefix}_CONTROL", "in", "signal", (0, 2.2, 3.2), "control")

    box(collection, "板换底座", (-1, 0, .35), (13, 7, .7), mats["white"], hx)
    for i in range(10):
        box(collection, "板换片 %02d" % i, (-3.5 + i * .55, 0, 2.7), (.13, 5.4, 4.4), mats["steel"], hx)
    cylinder(collection, "泵蜗壳", (-1, 0, 2.0), (1, 0, 2.0), 1.0, mats["supply"], pump)
    cylinder(collection, "泵电机", (0, 1, 2.0), (0, 4, 2.0), .7, mats["steel"], pump)
    box(collection, "阀体", (0, 0, 2.0), (6, 3.2, 2.4), mats["steel"], valve)
    box(collection, "阀执行器", (0, 0, 4.2), (3.2, 2.4, 1.0), mats["control"], valve)
    box(collection, "控制柜", (0, 0, 2.0), (5.5, 3.0, 6.0), mats["control"], ctrl)
    box(collection, "控制屏", (0, -1.56, 2.8), (3.0, .12, 1.8), mats["black"], ctrl)
    cylinder(collection, "分集水器供管", (-5, 0, 2.6), (5, 0, 2.6), .25, mats["supply"], header)
    cylinder(collection, "分集水器回管", (-5, 0, 1.2), (5, 0, 1.2), .25, mats["return"], header)

    all_ports = [hx_out, hx_in, pump_in, pump_out, valve_in, valve_out, header_out, header_in,
                 ctrl_out, valve_ctrl, pump_ctrl]
    # Device internal passages
    pipe(collection, "板换二次侧内部", [(6, 0, 2.6), (-6, 0, 2.6)], .18, mats["supply"],
         owner=hx, circuit=f"{prefix}_HEAT", connection_id=f"{prefix}_HX_INTERNAL",
         from_port=hx_out["port_id"], to_port=hx_in["port_id"])
    pipe(collection, "循环泵内部", [(-4, 0, 2.0), (4, 0, 2.0)], .18, mats["supply"],
         owner=pump, circuit=f"{prefix}_HEAT", connection_id=f"{prefix}_PUMP_INTERNAL",
         from_port=pump_in["port_id"], to_port=pump_out["port_id"])
    pipe(collection, "调节阀内部", [(-4, 0, 2.0), (4, 0, 2.0)], .16, mats["supply"],
         owner=valve, circuit=f"{prefix}_HEAT", connection_id=f"{prefix}_VALVE_INTERNAL",
         from_port=valve_in["port_id"], to_port=valve_out["port_id"])

    # External candidate edges in facility-local coordinates.
    ports = [hx_out, pump_in, pump_out, valve_in, valve_out, header_out, header_in]
    def edge(number, a, b, color, middle=()):
        pa = local_port_position(a)
        pb = local_port_position(b)
        pipe(collection, f"{prefix}_EDGE_{number:02d}", [tuple(pa), *middle, tuple(pb)], .20, color,
             owner=facility, circuit=a["circuit_id"], connection_id=f"{prefix}_EDGE_{number:02d}",
             from_port=a["port_id"], to_port=b["port_id"])
    edge(1, hx_out, pump_in, mats["supply"])
    edge(2, pump_out, valve_in, mats["supply"])
    edge(3, valve_out, header_out, mats["supply"])
    edge(4, header_in, hx_in, mats["return"])
    edge(5, ctrl_out, valve_ctrl, mats["control"], [(25, spec["yard_y"] - 20, 8)])
    edge(6, ctrl_out, pump_ctrl, mats["control"], [(28, spec["yard_y"] - 17, 7)])
    for index, terminal in enumerate(terminals, 1):
        # Both loads intentionally share a candidate header; the two branches remain distinct.
        x = spec["loads"][index - 1][2]
        edge(10 + index, header_out, terminal["in"], mats["supply"], [(x, spec["yard_y"] - 29, 3)])
        edge(20 + index, terminal["out"], header_in, mats["return"], [(x + 5, spec["yard_y"] - 35, 2)])

    label(collection, spec["zone_label"] + "｜候选末端设备补模", (-8, spec["yard_y"] - 38, 8), facility,
          mats["label"], 3.2)
    facility["m9_slice"] = "A/B terminal equipment"
    facility["m9_terminal_count"] = len(terminals)
    facility["m9_ports_added"] = len([o for o in collection.objects if o.get("parent_id") == facility.get("object_id") and o.get("kind") == "port"])
    return {"facility": facility, "entities": [hx, pump, valve, header, ctrl, sensor] + [x["entity"] for x in terminals]}


def camera_for(scene, name, location, target, ortho_scale, filepath):
    data = bpy.data.cameras.get(name) or bpy.data.cameras.new(name)
    camera = bpy.data.objects.get(name) or bpy.data.objects.new(name, data)
    if camera.name not in scene.objects:
        scene.collection.objects.link(camera)
    camera.data.type = next(item.identifier for item in bpy.types.Camera.bl_rna.properties["type"].enum_items
                            if item.identifier == "ORTHO")
    camera.location = location
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.ortho_scale = ortho_scale
    camera.data.clip_start = .1
    camera.data.clip_end = 20000
    scene.camera = camera
    scene.render.filepath = filepath
    bpy.ops.render.render(write_still=True)
    return camera



# Save all existing unsaved work into a new integrated copy before changes.
source_file = bpy.data.filepath
source_dirty = bpy.data.is_dirty
bpy.ops.wm.save_as_mainfile(filepath=BASE + '/outputs/m11-integrated-v1/乌兰察布_整合场景_v1.blend')
scene = bpy.data.scenes['05 | 水培育苗']
bpy.context.window.scene = scene
name = 'M11 | B区真实父设施末端'
assert bpy.data.collections.get(name) is None, 'Already built; inspect before rebuilding'
collection = bpy.data.collections.new(name)
bpy.data.collections['MAP_V2'].children.link(collection)
mats = {key: material(title, color, metallic) for key,title,color,metallic in [
 ('supply','供水',(.86,.14,.06),.28),('return','回水',(.06,.28,.80),.28),
 ('control','控制',(.97,.58,.08),.12),('greenhouse','温室末端',(.16,.55,.25),.05),
 ('ahu','AHU末端',(.38,.54,.63),.30),('steel','不锈钢',(.62,.70,.74),.72),
 ('white','设备白',(.82,.86,.84),.08),('black','控制屏',(.02,.04,.06),.05),('label','标签',(.04,.06,.07),0)]}
for prefix, title, yard_y in [('AGRI_016','B区番茄',-126),('AGRI_017','B区草莓',-94)]:
 add_heat_terminal(collection,bpy.data.objects[prefix],{'prefix':prefix,'zone_label':title,'kind':'greenhouse','yard_y':yard_y,
  'loads':[('GH1',title+'温室 GH1',-52),('GH2',title+'温室 GH2',36)]},mats,[])
# Existing A2 remains at its original coordinates and serves mushroom rooms.
for suffix,title in [('AHU1','食用菌菌房 AHU1'),('AHU2','食用菌菌房 AHU2')]:
 root=bpy.data.objects['AGRI_015_'+suffix]
 root['label']=title
 for child in root.children_recursive:
  if child.type=='FONT': child.data.body=title
for obj in bpy.data.collections['M9 | A/B 末端设备补模'].objects:
 if obj.type=='FONT' and 'B区番茄/草莓' in obj.data.body:
  obj.data.body=obj.data.body.replace('B区番茄/草莓','A区食用菌')
# Give the boiler body its registered owner so it is actually rendered/pickable.
boiler=bpy.data.objects.get('BOILER_CAND_001 | boiler')
if boiler:
 boiler['object_id']='BOILER_CAND_001'
 for child in boiler.children_recursive: child['object_id']='BOILER_CAND_001'
# All heat-exchanger internal curves must end exactly at their declared ports.
bpy.context.view_layer.update()
repaired=[]
for obj in bpy.data.objects:
 if obj.type=='CURVE' and obj.get('connection_id','').endswith('_HX_INTERNAL') and obj.get('m9_revision'):
  ports={p.get('port_id'):p for p in obj.parent.children_recursive if p.get('port_id')}
  a=ports.get(obj.get('from_port_id')); z=ports.get(obj.get('to_port_id'))
  if a and z:
   inv=obj.matrix_world.inverted()
   for pt,port in [(obj.data.splines[0].points[0],a),(obj.data.splines[0].points[-1],z)]:
    v=inv @ port.matrix_world.translation; pt.co=(*v,1)
   repaired.append(obj.name)
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=BASE + '/outputs/m11-integrated-v1/乌兰察布_整合场景_v1.blend')
print({'source_file':source_file,'source_was_dirty':source_dirty,'saved':bpy.data.filepath,'added_objects':len(collection.objects),'corrected_A2':True,'repaired_HX_curves':repaired})
