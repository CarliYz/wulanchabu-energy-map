"""Publish only after the new model and previews exist; keep the M11 assets intact."""
import hashlib
import json
import struct
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
FOLDER=ROOT/'web/map-prototype'
ASSETS=ROOT/'web/map-viewer/assets/integrated-v2'
QC=ROOT/'qc/m12-connected-v1'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    graph=json.loads((QC/'graph.json').read_text())
    for id in ['DRY_019','STORE_012','HUB_011','BOILER_CAND_001']:
        assert (ASSETS/(id+'.png')).is_file(),id
    blob=(ASSETS/'facilities.glb').read_bytes(); n=struct.unpack_from('<I',blob,12)[0]
    doc=json.loads(blob[20:20+n]);indices={node.get('name'):i for i,node in enumerate(doc['nodes'])}
    graph['asset_sha256']=sha(ASSETS/'facilities.glb')
    graph['parent_previews']={id:dict(preview_url=f'../map-viewer/assets/integrated-v2/{id}.png',model_revision=graph['revision'])
                            for id in ['DRY_019','STORE_012','HUB_011','BOILER_CAND_001']}
    (FOLDER/'m10-system-runtime.json').write_text(json.dumps(graph,ensure_ascii=False,indent=2)+'\n')
    entities=[];sources={}
    for file in ['facility-registry.json','c1-runtime.json','ab-terminal-runtime.json','m10-system-runtime.json']:
        path=FOLDER/file;entities.extend(json.loads(path.read_text())['objects']);sources[str(path.relative_to(ROOT))]=sha(path)
    asset=json.loads((QC/'before/integrated-asset.json').read_text())
    asset.update(revision=graph['revision'],asset_url=graph['asset_url'],sha256=graph['asset_sha256'],
                 entity_nodes={o['object_id']:indices[o['object_id']] for o in entities},sources=sources,
                 blender_source=graph['blender_source'],scene_index=doc.get('scene',0))
    (FOLDER/'integrated-asset.json').write_text(json.dumps(asset,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'entities':len(entities),'ports':len(graph['ports']),'connections':len(graph['connections']),'sha256':asset['sha256']}))


if __name__=='__main__': main()
