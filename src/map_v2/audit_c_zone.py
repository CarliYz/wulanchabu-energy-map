"""Read-only audit of the live C1 model. Run through the Blender MCP.

This checks visible component completeness and centerline joins, not hydraulic
capacity, thermal safety or an approved engineering design.
"""
import bpy
import json
from mathutils import Vector

parent = bpy.data.objects['AGRI_018']
children = list(parent.children_recursive)
names = [o.name for o in children]


def points(obj):
    if obj.type != 'CURVE':
        return []
    return [obj.matrix_world @ Vector(v.co[:3])
            for spline in obj.data.splines for v in spline.points]


def point_segment_distance(p, a, b):
    delta = b - a
    if not delta.length_squared:
        return (p - a).length
    t = max(0, min(1, (p - a).dot(delta) / delta.length_squared))
    return (p - (a + t * delta)).length


joins = []
for label, word in [('supply', '供水'), ('return', '回水')]:
    terminal = bpy.data.objects.get('AGRI_018 末端' + word)
    terminal_points = points(terminal) if terminal else []
    headers = [o for o in children if o.name.startswith('温室' + word)]
    for header in headers:
        hp = points(header)
        gap = min((point_segment_distance(hp[0], a, b)
                   for a, b in zip(terminal_points, terminal_points[1:])),
                  default=float('inf'))
        joins.append({'circuit': label, 'header': header.name,
                      'inlet_to_terminal_centerline_gap_m': round(gap, 4),
                      'pass': gap <= 0.05})

equipment_terms = {
    'circulation_pump': ['循环泵', '温控泵'],
    'temperature_valve': ['混水阀', '调节阀'],
    'temperature_sensor': ['温度传感', '温度测点'],
    'control_cabinet': ['控制柜', 'PLC'],
    'nutrient_tank': ['营养液箱', '营养液罐'],
    'nutrient_pump': ['营养液泵'],
}
equipment = {key: [n for n in names if any(t in n for t in terms)]
             for key, terms in equipment_terms.items()}
report = {
    'requirement_revision': 'ui-design-v2+c-zone-completeness-v1',
    'source_file': bpy.data.filepath,
    'live_file_dirty': bpy.data.is_dirty,
    'evidence_scope': 'live in-memory model; saved file identity is recorded by host',
    'asset_id': parent.name,
    'connection_status': parent.get('connection_status'),
    'child_count': len(children),
    'equipment': equipment,
    'header_joins': joins,
    'pass': all(equipment.values()) and len(joins) == 4 and all(j['pass'] for j in joins),
    'exclusions': ['Hydraulic and thermal sizing', 'nutrient flow simulation',
                   'candidate external route is not an operating heat connection'],
}
print(json.dumps(report, ensure_ascii=False))
