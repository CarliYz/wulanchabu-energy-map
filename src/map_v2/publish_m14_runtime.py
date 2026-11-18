"""Publish M14 sensor geometry without replacing historical assets."""
import argparse
import hashlib
import json
import shutil
import struct
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
FOLDER=ROOT/'web/map-prototype'
ASSETS=ROOT/'web/map-viewer/assets/integrated-v3'
QC=ROOT/'qc/m14-sensors-integrated-v1'
REV='m14-sensors-integrated-v1'
BLEND='outputs/m14-sensors-integrated-v1/乌兰察布_测点整合场景_v1.blend'
GLB='web/map-viewer/assets/integrated-v3/facilities.glb'
PARENTS=['AGRI_014','AGRI_015','AGRI_016','AGRI_017']
IDS=[p+'_SENSOR' for p in PARENTS]

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,data): path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')

def publish():
    before=QC/'before';before.mkdir(exist_ok=True)
    for name in ['ab-terminal-runtime.json','integrated-asset.json','audit-manifest.json','geographic-review-source.mjs']:
        if not (before/name).exists():shutil.copy2(FOLDER/name,before/name)
    for oid in IDS:
        shutil.copy2(ROOT/'outputs/m14-agriculture-sensors-v1'/(oid+'.png'),ASSETS/(oid+'.png'))
    blob=(ROOT/GLB).read_bytes();length=struct.unpack_from('<I',blob,12)[0]
    doc=json.loads(blob[20:20+length]);indices={n.get('name'):i for i,n in enumerate(doc['nodes'])}
    graph=json.loads((FOLDER/'ab-terminal-runtime.json').read_text())
    graph.update(revision=REV,requirement_revision=graph['requirement_revision'].split('+M14-four-visible-sensors')[0]+'+M14-four-visible-sensors',
        asset_url='../map-viewer/assets/integrated-v3/facilities.glb',asset_sha256=sha(ROOT/GLB),blender_source=BLEND)
    for obj in graph['objects']:
        oid=obj['object_id'];preview=oid if oid in IDS else obj['parent_id']
        obj['preview_url']='../map-viewer/assets/integrated-v3/'+preview+'.png'
        obj['model_revision']=REV
        if oid in IDS:
            obj['model_status']='schematic_proxy_unconnected'
            obj['description']='温度探杆与流量仪表示意样件，未接管；尚无信号端口、厂家、量程或实测读数，现场安装位置待核。'
            obj['gaps']=list(dict.fromkeys(obj['gaps']+['当前为未接管样件，管路安装点与PLC信号端口待设计核验']))
    for zone in graph['zones']:
        parent=zone['parent_id']
        zone['preview_url']='../map-viewer/assets/integrated-v3/'+parent+'.png'
        zone['semantic_root_nodes']={o['object_id']:indices[o['object_id']] for o in graph['objects'] if o['parent_id']==parent}
    graph['rendered_previews']=[{'path':'../map-viewer/assets/integrated-v3/'+oid+'.png','sha256':sha(ASSETS/(oid+'.png'))} for oid in PARENTS+IDS]
    write(FOLDER/'ab-terminal-runtime.json',graph)
    asset=json.loads((FOLDER/'integrated-asset.json').read_text())
    objects=[];sources={}
    for name in ['facility-registry.json','c1-runtime.json','ab-terminal-runtime.json','m10-system-runtime.json']:
        file=FOLDER/name;objects.extend(json.loads(file.read_text())['objects']);sources[str(file.relative_to(ROOT))]=sha(file)
    asset.update(revision=REV,asset_url=graph['asset_url'],sha256=graph['asset_sha256'],blender_source=BLEND,
        scene_index=doc.get('scene',0),sources=sources,entity_nodes={o['object_id']:indices[o['object_id']] for o in objects},
        semantic_only_entities=[])
    assert len(asset['entity_nodes'])==85
    write(FOLDER/'integrated-asset.json',asset)

def refresh_audit():
    audit=json.loads((FOLDER/'audit-manifest.json').read_text())
    old_glb=audit['web_model']['path'];old_blend=audit['blender']['scene_file']
    audit['runtime_revision']=REV+' · M13公开地理复核交互'
    audit['requirement_revision']=audit['requirement_revision'].split('+M14-four-visible-sensors')[0]+'+M14-four-visible-sensors'
    audit['blender'].update(scene_file=BLEND,scene_file_sha256=sha(ROOT/BLEND))
    audit['web_model'].update(path=GLB,sha256=sha(ROOT/GLB),pickable_objects=85)
    for name in ['ab_terminal_model','m10_system_model']:
        item=audit['web_model'][name]
        item.update(path=GLB,sha256=sha(ROOT/GLB),blend_path=BLEND,blend_sha256=sha(ROOT/BLEND))
        if 'included_in_integrated_asset' in item:item['included_in_integrated_asset']=GLB
    for key,value in list(audit['sources'].items()):
        if key.endswith('_path'):audit['sources'][key.removesuffix('_path')+'_sha256']=sha(ROOT/value)
    for item in audit['source_inventory']:
        if item['path']==old_glb:item['path']=GLB
        if item['path']==old_blend:item['path']=BLEND
        if any(item['path'].endswith('/'+oid+'.png') for oid in PARENTS):
            item['path']='web/map-viewer/assets/integrated-v3/'+Path(item['path']).name
        item['sha256']=sha(ROOT/item['path'])
        if item['path'] in {GLB,BLEND,'web/map-prototype/ab-terminal-runtime.json','web/map-prototype/integrated-asset.json'} or '/integrated-v3/' in item['path']:
            item['version']=REV
    paths={'web/map-viewer/assets/integrated-v3/'+oid+'.png' for oid in PARENTS+IDS}
    existing={i['path'] for i in audit['source_inventory']}
    for path in sorted(paths-existing):
        audit['source_inventory'].append({'label':'农业模型图 '+Path(path).stem,'path':path,'version':REV,
            'sha256':sha(ROOT/path),'status':'candidate','status_label':'同版候选模型；测点未接管'})
    limit='M14四农业测点已有可见仪表示意网格；样件未接管，无PLC信号端口、厂家、量程、实测读数或现场安装依据。'
    if limit not in audit['limitations']:audit['limitations'].append(limit)
    write(FOLDER/'audit-manifest.json',audit)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--audit-only',action='store_true')
    args=parser.parse_args()
    if not args.audit_only:publish()
    refresh_audit()
    print(json.dumps({'revision':REV,'glb_sha256':sha(ROOT/GLB),'entities':85,'visible_sensors':4}))
