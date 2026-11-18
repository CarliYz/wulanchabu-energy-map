"""Refresh current-source audit hashes after model export and UI changes."""
import collections
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
FOLDER=ROOT/'web/map-prototype'


def sha(path): return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()


def main():
    path=FOLDER/'audit-manifest.json';audit=json.loads(path.read_text())
    graph=json.loads((FOLDER/'m10-system-runtime.json').read_text())
    asset=json.loads((FOLDER/'integrated-asset.json').read_text())
    blend=graph['blender_source'];glb='web/map-viewer/assets/integrated-v2/facilities.glb'
    audit['runtime_revision']='working-tree · m12-connected-v1'
    audit['requirement_revision']=graph['requirement_revision']
    audit['blender'].update(scene_file=blend,scene_file_sha256=sha(blend))
    audit['web_model'].update(path=glb,sha256=sha(glb),pickable_objects=len(asset['entity_nodes']))
    audit['web_model']['ab_terminal_model'].update(path=glb,sha256=sha(glb),blend_path=blend,blend_sha256=sha(blend))
    renders=[f'web/map-viewer/assets/integrated-v2/{id}.png' for id in ['DRY_019','STORE_012','HUB_011','BOILER_CAND_001']]
    audit['web_model']['m10_system_model'].update(path=glb,sha256=sha(glb),blend_path=blend,blend_sha256=sha(blend),
        objects=len(graph['objects']),ports=len(graph['ports']),connections=len(graph['connections']),
        render_paths=renders,render_sha256={p:sha(p) for p in renders},included_in_integrated_asset=glb)
    audit['sources']['m10_graph_path']='web/map-prototype/m10-graph.mjs'
    for key,value in list(audit['sources'].items()):
        if key.endswith('_path'):audit['sources'][key.removesuffix('_path')+'_sha256']=sha(value)
    audit['limitations']=[s for s in audit['limitations'] if '24条关系' not in s]
    limitation='系统30对象/90端口/83条候选模型连接；C2并联接管为新设计提案，现场喷嘴、独立配准、水力和工程穿越未验收。'
    if limitation not in audit['limitations']:audit['limitations'].append(limitation)
    obsolete={'A/B 末端 GLB','A/B Blender 副本','A区末端验收图','B区末端验收图'}
    entries=[i for i in audit['source_inventory'] if i['label'] not in obsolete]
    remap={'Blender 场景':blend,'网页 GLB':glb,'M10 系统设备 GLB':glb,'M10 Blender 副本':blend,
           **dict(zip(['C2 系统渲染图','PTES 系统渲染图','HUB 角色映射渲染图','条件电锅炉候选渲染图'],renders))}
    for item in entries:
        if item['label'] in remap:item['path']=remap[item['label']]
        item['sha256']=sha(item['path'])
        if item['path'] in {glb,blend,'web/map-prototype/app.mjs','web/map-prototype/integrated-asset.json','web/map-prototype/m10-system-runtime.json','web/map-prototype/m10-relations.mjs'} or item['path'] in renders:
            item['version']='m12-connected-v1'
    if not any(i['path']=='web/map-prototype/m10-graph.mjs' for i in entries):
        entries.append(dict(label='系统候选端口校验',path='web/map-prototype/m10-graph.mjs',version='m12-connected-v1',
                            sha256=sha('web/map-prototype/m10-graph.mjs'),status='verified',status_label='合同校验代码；非工程验收'))
    audit['source_inventory']=entries
    path.write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'sources':len(entries),'runtime':audit['runtime_revision'],'blend_sha256':sha(blend),'glb_sha256':sha(glb)}))


if __name__=='__main__': main()
