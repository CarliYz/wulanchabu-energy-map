"""Detour the NEW schematic corridor around planned model footprints."""
from pathlib import Path
import json
from pyproj import Transformer

ROOT=Path(__file__).resolve().parents[2]
g=json.loads((ROOT/'data/map-v2/geographic-manifest.json').read_text())
f={x['id']:x for x in g['features']}
city_ll=[113.161,41.04]
x,y=Transformer.from_crs(4326,32649,always_xy=True).transform(*city_ll)
city=[x-g['origin'][0],y-g['origin'][1],0]
sizes={'STORE_012':(320,240),'DEMO_013':(155,135),'AGRI_014':(240,195),
       'AGRI_015':(180,115),'AGRI_016':(250,220),'AGRI_017':(190,155),
       'AGRI_018':(190,150),'DRY_019':(190,155)}
obstacles=[]
for fid,(w,h) in sizes.items():
    xx,yy,_=f[fid]['xyz']; margin=55
    obstacles.append((fid,(xx-w/2-margin,yy-h/2-margin,xx+w/2+margin,yy+h/2+margin)))


def crosses(a,b,box):
    low,high=0.,1.
    for dim in (0,1):
        d=b[dim]-a[dim]
        if abs(d)<1e-9:
            if not box[dim]<a[dim]<box[dim+2]: return False
        else:
            v0=(box[dim]-a[dim])/d; v1=(box[dim+2]-a[dim])/d
            low=max(low,min(v0,v1)); high=min(high,max(v0,v1))
    return low+1e-7<high


points=[p[:] for p in f['PIPE_P2_SEED']['xyz'][:-1]]+[city]
points=[p for p in points if not any(b[0]<p[0]<b[2] and b[1]<p[1]<b[3] for _,b in obstacles)]
detours=[]
for attempt in range(12):
    changed=False; next_points=[points[0]]
    for a,b in zip(points[:-1],points[1:]):
        hit=next(((fid,box) for fid,box in obstacles if crosses(a,b,box)),None)
        if hit:
            fid,box=hit
            left=box[0]-25; bottom=box[1]-25; top=box[3]+25
            via=[[left,bottom,0],[left,top,0]] if b[1]>=a[1] else [[left,top,0],[left,bottom,0]]
            next_points.extend(via); detours.append(fid); changed=True
        next_points.append(b)
    points=next_points
    if not changed: break
else: raise RuntimeError('Cannot find a clear schematic corridor')
for a,b in zip(points[:-1],points[1:]):
    for fid,box in obstacles: assert not crosses(a,b,box),fid
out={'city_candidate_lonlat':city_ll,'city_candidate_xyz':city,'status':'new_design_candidate_unverified',
     'main_candidate_xyz':points,'detoured_around_asset_ids':sorted(set(detours)),
     'routing_rule':'New schematic corridor avoids model footprints plus 55m buffer; not a road, land or crossing approval',
     'legacy_route_unchanged':True}
(ROOT/'data/map-v2/design-nodes.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print({'outcome':'pass','waypoints':len(points),'detours':out['detoured_around_asset_ids']})
