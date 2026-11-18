"""Prepare a reviewed Blender MCP request from source and current frozen results."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--phase',type=int,choices=(1,2,3),default=3)
    p.add_argument('--input',type=Path,default=ROOT/'data/inputs.csv')
    p.add_argument('--results',type=Path,default=ROOT/'data/generated/results.json')
    p.add_argument('--blend',type=Path)
    p.add_argument('--request',type=Path,required=True)
    args=p.parse_args()
    payload=json.loads(args.results.read_text())
    params=json.loads((ROOT/'data/parameters.json').read_text())
    frozen={'storage_initial_mwh':0,'storage_capacity_mwh':4,'charge_limit_mw':1,'discharge_limit_mw':2}
    if any(params.get(k)!=v for k,v in frozen.items()):
        raise ValueError('display v1 uses frozen storage parameters; revise design before changing them')
    if payload['input_sha256']!=hashlib.sha256(args.input.read_bytes()).hexdigest():
        raise ValueError('stale result: input digest mismatch; recalculate before building')
    if payload['parameters_sha256']!=hashlib.sha256((ROOT/'data/parameters.json').read_bytes()).hexdigest():
        raise ValueError('stale result: parameter digest mismatch')
    if any(row['dt_h'] != 1 for row in payload['rows']):
        raise ValueError('display v1 requires 1h steps; revise timeline and labels before changing duration')
    dest=args.blend or ROOT/'checkpoints'/f'{args.phase:02d}-energy.blend'
    dest.parent.mkdir(exist_ok=True,parents=True)
    body=(ROOT/'src/build_scene.py').read_text()+'\nscene=build('+repr(payload)+', phase='+str(args.phase)+')\n'
    body+='bpy.ops.file.pack_all()\nbpy.ops.wm.save_as_mainfile(filepath='+repr(str(dest.resolve()))+')\n'
    args.request.parent.mkdir(exist_ok=True,parents=True)
    args.request.write_text(json.dumps({'tool':'execute_blender_code','arguments':{'code':body}},ensure_ascii=False))
    print(json.dumps({'operation':'prepare_mcp','outcome':'pass','phase':args.phase,'input_sha256':payload['input_sha256'],'destination':str(dest)}))
