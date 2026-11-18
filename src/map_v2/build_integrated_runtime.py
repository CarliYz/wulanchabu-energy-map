"""Build agricultural contracts from their original facility ownership and one GLB."""
import copy
import json
from pathlib import Path
import build_ab_runtime as terminal

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / 'web/map-viewer/assets/integrated-v1'
GLB = ASSETS / 'facilities.glb'
REGISTRY = ROOT / 'web/map-prototype'


def main():
    original = json.loads((ROOT / 'qc/m11-integrated-v1/before/ab-terminal-runtime.json').read_text())
    graph = copy.deepcopy(original)
    parents = {o['object_id']: o for o in json.loads((REGISTRY/'facility-registry.json').read_text())['objects']}
    terminal.ASSET_ROOT = '../map-viewer/assets/integrated-v1'
    terminal.REVISION = 'm11-integrated-v1'
    graph.update(revision=terminal.REVISION, requirement_revision='地图场景方案_v2:A1-A2-B1-B2+m11-integrated-v1',
                 asset_url=terminal.ASSET_ROOT+'/facilities.glb', asset_sha256=terminal.sha256(GLB),
                 blender_source='outputs/m11-integrated-v1/乌兰察布_整合场景_v1.blend', blender_scene='06 | 全区整合交互')
    for obj in graph['objects']:
        prefix = obj['parent_id']
        if prefix == 'AGRI_015':
            obj['zone_label'] = 'A区食用菌 / 菌房空气处理'
            if obj['object_id'].endswith('_AHU1'): obj['name'] = '食用菌菌房 AHU1'
            if obj['object_id'].endswith('_AHU2'): obj['name'] = '食用菌菌房 AHU2'
            if obj['object_id'].endswith(('_AHU1','_AHU2')):
                obj['description'] = '食用菌菌房 AHU 水盘管接板换二次侧闭式热水；仅向空气传热，不把热水混入空气或营养液，负荷与控制参数待核。'
        obj['preview_url'] = f'{terminal.ASSET_ROOT}/{prefix}.png'
        obj['model_revision'] = terminal.REVISION
    for obj in graph['ports']+graph['connections']:
        if obj['parent_id'] == 'AGRI_015': obj['zone_label'] = 'A区食用菌 / 菌房空气处理'
    for prefix, name, yard in [('AGRI_016','B区番茄',-126),('AGRI_017','B区草莓',-94)]:
        common = [('HX','隔离板换：仅传热不混水','heat_exchanger',(-8,yard,2)),
                  ('PUMP','二次侧循环泵','pump',(-8,yard-10,2)),
                  ('VALVE','调节阀与隔离阀','valve',(-8,yard-20,2)),
                  ('HEADER','供回分集水器','header',(-8,yard-29,2)),
                  ('CTRL','PLC 控制柜','controller',(34,yard-20,2)),
                  ('SENSOR','温度/流量测点','sensor',(20,yard-20,2)),
                  ('GH1',name+'温室 GH1','terminal',(-52,yard-30,2)),
                  ('GH2',name+'温室 GH2','terminal',(36,yard-30,2))]
        equipment = [(prefix+'_'+s,n,k,v) for s,n,k,v in common]
        objects, ports, edges = terminal.build_zone(parents[prefix],prefix,name,prefix+'.png',equipment,prefix+'_HEAT')
        graph['objects'].extend(objects); graph['ports'].extend(ports); graph['connections'].extend(edges)
    graph['parent_facilities'] = [{'object_id':i,'name':parents[i]['name'],'zone':'A区' if i in ['AGRI_014','AGRI_015'] else 'B区'}
                                  for i in ['AGRI_014','AGRI_015','AGRI_016','AGRI_017']]
    doc = terminal.read_glb_document(GLB)
    indices = {n.get('name'):i for i,n in enumerate(doc['nodes'])}
    graph['zones'] = [{'parent_id':p['object_id'],'zone_label':p['zone'],
                       'semantic_root_nodes':{o['object_id']:indices[o['object_id']] for o in graph['objects'] if o['parent_id']==p['object_id']},
                       'preview_url':terminal.ASSET_ROOT+'/'+p['object_id']+'.png'} for p in graph['parent_facilities']]
    graph['rendered_previews'] = [{'path':f'{terminal.ASSET_ROOT}/{p["object_id"]}.png','sha256':terminal.sha256(ASSETS/(p['object_id']+'.png'))}
                                 for p in graph['parent_facilities']]
    graph['engineering_gaps'] = ['设施级独立配准和控制点未完成','道路/铁路/水域穿越待核','流量、泵扬程、管径和热负荷未完成计算']
    (REGISTRY/'ab-terminal-runtime.json').write_text(json.dumps(graph,ensure_ascii=False,indent=2)+'\n')
    all_entities = []
    sources = {}
    for name in ['facility-registry.json','c1-runtime.json','ab-terminal-runtime.json','m10-system-runtime.json']:
        p=REGISTRY/name; sources[str(p.relative_to(ROOT))]=terminal.sha256(p)
        all_entities.extend(json.loads(p.read_text())['objects'])
    asset = {'revision':'m11-integrated-v1','asset_url':terminal.ASSET_ROOT+'/facilities.glb','sha256':terminal.sha256(GLB),
             'scene_index':doc.get('scene',0),'entity_nodes':{o['object_id']:indices[o['object_id']] for o in all_entities},
             'sources':sources,'blender_source':graph['blender_source'],
             'semantic_only_entities':[prefix+'_SENSOR' for prefix in ['AGRI_014','AGRI_015','AGRI_016','AGRI_017']],
             'boundary':'候选示意模型；地理配准、施工、水力及运行状态未验收'}
    (REGISTRY/'integrated-asset.json').write_text(json.dumps(asset,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'entities':len(all_entities),'agricultural_devices':len(graph['objects']),
                     'ports':len(graph['ports']),'connections':len(graph['connections']),'sha256':asset['sha256']}))


if __name__ == '__main__':
    main()
