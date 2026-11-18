"""Bind the reviewed system proposal to schematic ports, without altering shared contracts."""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QC = ROOT/'qc/m12-connected-v1'
REVISION = 'm12-connected-v1'


def main():
    QC.mkdir(exist_ok=True)
    before=QC/'before'; before.mkdir(exist_ok=True)
    for name in ['m10-system-runtime.json','integrated-asset.json','ab-terminal-runtime.json','audit-manifest.json']:
        target=before/name
        if not target.exists(): target.write_bytes((ROOT/'web/map-prototype'/name).read_bytes())
    graph=json.loads((before/'m10-system-runtime.json').read_text())
    bundle=ROOT/'qc/agent-b-349-phase2/bundle'
    proposal=json.loads((ROOT/'qc/agent-b-349-phase2/design.json').read_text())
    declarations=json.loads((bundle/'ports.json').read_text())
    design=json.loads((bundle/'connections.json').read_text())
    extra=copy.deepcopy(next(o for o in graph['objects'] if o['object_id']=='STORE_012_CHARGE_VRETURN'))
    extra.update(object_id='STORE_012_DIS_VRETURN',name='PTES 放热回水隔离阀候选',short_name='放热回水阀',
                 model_root_xyz=[-502.02801513671875,502.03912353515625,151.95858764648438],
                 circuits=['USER','PTES_CONTROL'],description='phase2 合同已有的独立放热回水阀，本批补齐候选几何。')
    graph['objects'].append(extra)
    ids={o['object_id'] for o in graph['objects']}|{'HUB_011','STORE_012','DRY_019'}
    ports={p['port_id']:copy.deepcopy(p) for p in declarations['ports'] if p['object_id'] in ids}
    # C2 is an explicit new proposal. Primary water and secondary water stay isolated.
    ports={id:p for id,p in ports.items() if not p['object_id'].startswith('DRY_019')}
    edges=[]
    def connect(id,a,b,role='supply',branch=None,origin='phase2'):
        pa,pb=ports[a],ports[b]
        assert (pa['medium'],pa['circuit_id'])==(pb['medium'],pb['circuit_id']),(id,a,b)
        assert (pa['direction'],pb['direction'])==(('in','out') if role=='internal' else ('out','in'))
        edges.append(dict(connection_id='M12_'+id,from_port_id=a,to_port_id=b,
            from_object_id=pa['object_id'],to_object_id=pb['object_id'],circuit_id=pa['circuit_id'],
            medium=pa['medium'],role=role,branch=branch,source=origin,status='candidate_unverified',
            model_status='schematic_connected',execution_allowed=False))
    for edge in design['connections']:
        a,b=edge['from_port_id'],edge['to_port_id']
        if a not in ports or b not in ports: continue
        id=edge['connection_id']
        branch='charge' if 'CHARGE' in id and 'DISCHARGE' not in id else 'discharge' if 'DISCHARGE' in id else None
        role='control' if ports[a]['medium']=='signal' else 'power' if ports[a]['medium']=='electricity' else 'return' if 'RETURN' in id else 'supply'
        connect(id,a,b,role,branch)
    # Keep only ports participating in this slice, plus isolated source/P1 interfaces.
    used={e[k] for e in edges for k in ['from_port_id','to_port_id']}
    used|={id for id,p in ports.items() if p['object_id'] in {'HUB_011_EVAP','HUB_011_P1_HX'} and p['circuit_id'] in {'SOURCE','P1_USER'}}
    ports={id:p for id,p in ports.items() if id in used}
    for i,passage in enumerate(proposal['internal_passages']):
        a,b=passage['in_port_id'],passage['out_port_id']
        if a in ports and b in ports:
            connect('PASSAGE_'+str(i),a,b,'internal')
            edges[-1]['requires']=passage['requires']

    def port(obj,circuit,direction,role='flow',medium='water'):
        id=f'{obj}:{circuit}:{direction}:{role}'
        ports[id]=dict(port_id=id,object_id=obj,circuit_id=circuit,medium=medium,direction=direction,role=role,source_ids=['M12_C2_PROPOSAL'])
        return id
    source_out=port('DRY_019','DRY_019_HEAT','out','primary_supply')
    source_in=port('DRY_019','DRY_019_HEAT','in','primary_return')
    load_in=port('DRY_019','C2_SECONDARY','in','process_supply')
    load_out=port('DRY_019','C2_SECONDARY','out','process_return')
    boost_in=port('DRY_019_BOOSTER','C2_SECONDARY','in')
    boost_out=port('DRY_019_BOOSTER','C2_SECONDARY','out')
    connect('C2_LOAD_SUPPLY',boost_out,load_in,origin='M12_C2_PROPOSAL')
    transfers=[t for t in design['energy_transfers'] if t['object_id'] in ids]
    for i in [1,2,3]:
        obj=f'DRY_019_HX_{i}'
        pi=port(obj,'DRY_019_HEAT','in');po=port(obj,'DRY_019_HEAT','out')
        si=port(obj,'C2_SECONDARY','in');so=port(obj,'C2_SECONDARY','out')
        connect(f'C2_HX{i}_SUPPLY',source_out,pi,origin='M12_C2_PROPOSAL')
        connect(f'C2_HX{i}_RETURN',po,source_in,'return',origin='M12_C2_PROPOSAL')
        connect(f'C2_HX{i}_SECONDARY_HOT',so,boost_in,origin='M12_C2_PROPOSAL')
        connect(f'C2_HX{i}_SECONDARY_RETURN',load_out,si,'return',origin='M12_C2_PROPOSAL')
        connect(f'C2_HX{i}_PRIMARY_INTERNAL',pi,po,'internal',origin='M12_C2_PROPOSAL')
        connect(f'C2_HX{i}_SECONDARY_INTERNAL',si,so,'internal',origin='M12_C2_PROPOSAL')
        transfers.append(dict(transfer_id=f'M12_TRANSFER_{obj}',object_id=obj,from_circuit_id='DRY_019_HEAT',
                              to_circuit_id='C2_SECONDARY',kind='heat_transfer_no_mass_flow',power_kw=None,source_ids=['M12_C2_PROPOSAL']))
    connect('C2_BOOST_INTERNAL',boost_in,boost_out,'internal',origin='M12_C2_PROPOSAL')
    connect('C2_PROCESS_INTERNAL',load_in,load_out,'internal',origin='M12_C2_PROPOSAL')
    power_out=port('DRY_019_POWER','DRY_019_POWER','out','power','electricity')
    power_in=port('DRY_019_BOOSTER','DRY_019_POWER','in','power','electricity')
    connect('C2_POWER',power_out,power_in,'power',origin='M12_C2_PROPOSAL')
    for obj in ['DRY_019_BOOSTER','DRY_019_HX_1','DRY_019_HX_2','DRY_019_HX_3']:
        control=port('DRY_019_CTRL','DRY_019_CONTROL','out','command','signal')
        actuator=port(obj,'DRY_019_CONTROL','in','command','signal')
        connect('C2_CONTROL_'+obj,control,actuator,'control',origin='M12_C2_PROPOSAL')

    # Local model sockets are explicitly distinct from field nozzle coordinates.
    by_object={}
    for p in ports.values(): by_object.setdefault(p['object_id'],[]).append(p)
    for oid,ps in by_object.items():
        counters={}
        for p in ps:
            key=(p['medium'],p['direction']);slot=counters.get(key,0);counters[key]=slot+1
            if p['medium']=='electricity': xyz=[0,-6,3+slot*2]
            elif p['medium']=='signal': xyz=[0,6,3+slot*2]
            else: xyz=[-6 if p['direction']=='in' else 6,slot*3-3,2 if p['circuit_id'] in {'USER','DRY_019_HEAT','SOURCE'} else 6]
            if oid=='DRY_019': xyz=[-85 if p['circuit_id']=='DRY_019_HEAT' else 10,-60 if p['direction']=='out' else 60,12]
            if oid=='STORE_012': xyz=[-95 if 'discharge' in p['role'] else 95,40 if p['direction']=='out' else -40,10]
            p['position']=dict(space='object_local_z_up',xyz_m=xyz,status='candidate_model_socket_not_field_nozzle')
    for obj in graph['objects']:
        obj['model_revision']=REVISION
        obj['circuits']=sorted({p['circuit_id'] for p in ports.values() if p['object_id']==obj['object_id']}) or obj['circuits']
        parent=obj['parent_id'] or obj['object_id']
        parent='HUB_011' if parent=='HUB_011' else parent
        obj['preview_url']=f'../map-viewer/assets/integrated-v2/{parent}.png'
        if obj['object_id'].startswith('DRY_019_HX_'):
            obj['description']='C2 三台板换并联的候选设计提案；一次与二次水隔离，仅传热，接管方式待专业核定。'
    graph.update(revision=REVISION,requirement_revision='M11+phase2-system-contract+M12-C2-proposal',
        asset_url='../map-viewer/assets/integrated-v2/facilities.glb',asset_sha256=None,
        blender_source='outputs/m12-connected-v1/乌兰察布_连接整合场景_v1.blend',
        ports=list(ports.values()),connections=edges,energy_transfers=transfers,
        energy_conversions=proposal['energy_conversions'],ptes=proposal['ptes'],execution_allowed=False,
        original_relations_status='superseded_by_declared_candidate_ports',
        boundary='候选模型连接；不是现场喷嘴、已施工管路或水力验收')
    (QC/'graph.json').write_text(json.dumps(graph,ensure_ascii=False,indent=2)+'\n')
    (ROOT/'outputs/m12-connected-v1').mkdir(exist_ok=True)
    (ROOT/'web/map-viewer/assets/integrated-v2').mkdir(exist_ok=True)
    print(json.dumps({'objects':len(graph['objects']),'ports':len(ports),'connections':len(edges),'draft':str(QC/'graph.json')}))


if __name__=='__main__': main()
