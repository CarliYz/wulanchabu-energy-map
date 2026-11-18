"""Read the actual live model. Host supplies frozen fixture expectations.

Checks endpoint geometry separately from logical topology; not hydraulic sizing.
"""
import bpy
import json
import math
from mathutils import Vector

root = bpy.data.objects['AGRI_018']
objects = list(root.children_recursive)
ports = {o['port_id']: o for o in objects if o.get('port_id')}
edges = {o['connection_id']: o for o in objects if o.get('connection_id')}
entities = {o['object_id']: o for o in objects
            if o.type == 'EMPTY' and o.get('object_id') and not o.get('port_id')}
failures = []


def require(condition, message):
    if not condition:
        failures.append(message)


def points(o):
    return [o.matrix_world @ Vector(p.co[:3]) for s in o.data.splines for p in s.points]


def distance_to_curve(p, curve):
    vs = points(curve)
    best = float('inf')
    for a,b in zip(vs,vs[1:]):
        d=b-a
        t=max(0,min(1,(p-a).dot(d)/d.length_squared)) if d.length_squared else 0
        best=min(best,(p-(a+t*d)).length)
    return best


require(len(ports)==len(EXPECTED_PORTS), 'port count differs from frozen C1 contract')
require(set(ports)=={p['port_id'] for p in EXPECTED_PORTS}, 'port IDs differ')
for p in EXPECTED_PORTS:
    o=ports.get(p['port_id'])
    require(o is not None, 'missing '+p['port_id'])
    if o is not None:
        require(o.get('object_id')==p['object_id'], 'owner '+p['port_id'])
        for key in ['direction','medium','circuit_id']:
            require(o.get(key)==p[key], key+' '+p['port_id'])
        require(all(math.isfinite(v) for v in o.matrix_world.translation), 'nonfinite port')

joins=[]
for e in EXPECTED_EDGES:
    o=edges.get(e['connection_id'])
    require(o is not None, 'missing curve '+e['connection_id'])
    if o is None:
        continue
    require(o.get('from_port_id')==e['from_port_id'] and o.get('to_port_id')==e['to_port_id'],
            'wrong endpoint IDs '+e['connection_id'])
    a,b=ports[e['from_port_id']],ports[e['to_port_id']]
    require(a['medium']==b['medium'] and a['circuit_id']==b['circuit_id'], 'mixed circuit')
    vs=points(o)
    gaps=[(vs[0]-a.matrix_world.translation).length,(vs[-1]-b.matrix_world.translation).length]
    require(max(gaps)<.002, 'endpoint gap '+e['connection_id'])
    joins.append({'connection_id':e['connection_id'],'endpoint_gaps_m':gaps})

# Read existing greenhouse headers after reparenting: the four original gaps
# are resolved through secondary headers, not by mixing primary water into crops.
header_checks=[]
for n,ghid,x in [('006','AGRI_018_GH1',-71.5),('007','AGRI_018_GH2',-4.5)]:
    for word,direction,role in [('供水','in','supply'),('回水','out','return')]:
        o=bpy.data.objects['温室'+word+'.'+n]
        pid=ghid+':C1_HEAT:'+direction+':'+ghid+'_'+role
        gap=distance_to_curve(ports[pid].matrix_world.translation,o)
        require(gap<.002,'legacy greenhouse header gap '+o.name)
        require(o.parent==entities[ghid], 'greenhouse owner '+o.name)
        header_checks.append({'header':o.name,'port_id':pid,'gap_m':gap})

for ghid in ['AGRI_018_GH1','AGRI_018_GH2']:
    gh=entities[ghid]
    children=list(gh.children_recursive)
    require(sum('散热支路' in o.name for o in children)==5, 'five heating loops '+ghid)
    require(sum('水培槽循环' in o.name for o in children)==10, 'ten nutrient channels '+ghid)
    require(sum(o.name.startswith('水培槽') for o in children)==10, 'existing nutrient beds '+ghid)

require(root.get('connection_status')=='future_candidate_not_P1_connected', 'candidate status lost')
for n in ['AGRI_018 用户隔离换热站','AGRI_018 末端供水','AGRI_018 末端回水']:
    require(bpy.data.objects[n].hide_render and bpy.data.objects[n].hide_viewport,
            'old bypass still visible '+n)

bounds={}
for oid,owner in entities.items():
    vertices=[o.matrix_world @ Vector(v) for o in owner.children_recursive
              if o.type in {'MESH','CURVE'} and not o.hide_render for v in o.bound_box]
    require(bool(vertices),'empty equipment '+oid)
    if vertices:
        bounds[oid]={'min':[min(v[i] for v in vertices) for i in range(3)],
                     'max':[max(v[i] for v in vertices) for i in range(3)]}

report={'revision':root.get('m8_revision'),'status':'pass' if not failures else 'fail',
        'scope':'live schematic geometry and fixture-linked topology; not product/engineering acceptance',
        'source_file':bpy.data.filepath,'dirty':bpy.data.is_dirty,'object_id':'AGRI_018',
        'entity_count':len(entities),'port_count':len(ports),'connection_count':len(edges),
        'joins':joins,'greenhouse_headers':header_checks,'bounds_world_z_up':bounds,
        'failures':failures,'external_status':root.get('connection_status'),
        'not_verified':['hydraulic sizing','thermal sizing','equipment procurement',
                        'independent geographic registration','browser selection integration']}
print('C1_AUDIT_JSON:'+json.dumps(report,ensure_ascii=False))
