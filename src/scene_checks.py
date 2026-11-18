"""Checks evaluated Blender state against externally frozen result rows."""
import bpy


def signature(scene):
    scene.frame_set(170)
    return sorted((o['object_id'],o.type,tuple(round(v,6) for v in o.location),
                   tuple(round(v,6) for v in o.scale)) for o in scene.collection.all_objects)


def verify_scene(payload):
    scene=bpy.data.scenes['ENERGY_MVP']
    assert scene['input_sha256']==payload['input_sha256'], 'input identity mismatch'
    lookup={(r['scenario_id'],r['hour_index']):r for r in payload['rows']}
    ids=[o['object_id'] for o in scene.collection.all_objects]
    assert len(set(ids))==len(ids), 'duplicated persistent object ID'
    curves=[o for o in scene.collection.all_objects if 'water_loop' in o]
    assert len([o for o in curves if o['water_loop']=='primary'])==2
    assert len([o for o in curves if o['water_loop']=='secondary'])==8
    checks=[]
    for frame,scenario,t in [(85,'MVP_NORMAL',0),(104,'MVP_NORMAL',1),(122,'MVP_NORMAL',2),
                              (140,'MVP_NORMAL',3),(170,'MVP_NORMAL',6),
                              (220,'MVP_SOURCE_OUTAGE',4),(260,'MVP_SOURCE_OUTAGE',5),
                              (290,'MVP_SOURCE_OUTAGE',6),(330,'MVP_SOURCE_OUTAGE',7),
                              (350,'MVP_SOURCE_OUTAGE',8),(410,'MVP_SOURCE_OUTAGE',11)]:
        scene.frame_set(frame);r=lookup[(scenario,t)]
        for key in ['source_mw','delivered_mw','unserved_mw','storage_end_mwh','charge_mw','discharge_mw','curtailed_mw']:
            assert abs(scene[key]-r[key])<=.001,(frame,key,scene[key],r[key])
        active=[o for o in scene.collection.all_objects if not o.hide_render]
        power=[o for o in active if o.name.endswith('_power')]
        assert len(power)==1,('power label count',frame,len(power))
        assert power[0]['scenario_id']==scenario and power[0]['hour_index']==t
        assert f'交付 {r["delivered_mw"]:g} MW' in power[0].data.body
        assert f'未供 {r["unserved_mw"]:g} MW' in power[0].data.body
        markers=[o for o in active if o.name.startswith('ENERGY_flow_')]
        expected=dict(r,source_used=r['direct_mw']+r['charge_mw'])
        for o in markers:
            assert o['scenario_id']==scenario and o['hour_index']==t
            assert expected[o['flow_metric']]>0,('zero-flow marker',frame,o.name)
        if r['source_mw']==0:
            assert not any('primary_' in o.name or 'secondary_hot_' in o.name for o in markers)
        if r['delivered_mw']==0:
            assert not any('secondary_delivery' in o.name or 'storage_discharge' in o.name for o in markers)
        fill=bpy.data.objects['ENERGY_TES_DEMO.energy_fill']
        assert abs(fill.scale.z-max(.001,r['storage_end_mwh']/4))<1e-5
        checks.append(dict(frame=frame,scenario_id=scenario,t=t,delivered_mw=r['delivered_mw'],
                           unserved_mw=r['unserved_mw'],storage_end_mwh=r['storage_end_mwh'],active_flow_markers=len(markers)))
    for o in scene.collection.all_objects:
        if o.animation_data:assert not o.animation_data.drivers,'unexpected scripted driver'
    scene.frame_set(420)
    summary=bpy.data.objects['ENERGY_Summary']
    assert not summary.hide_render
    n=payload['summary']['MVP_NORMAL'];q=payload['summary']['MVP_SOURCE_OUTAGE']
    for phrase in [f'正常交付 {n["delivered_mwh"]:g}',
                   f'退出交付 {q["delivered_mwh"]:g} / 未供 {q["unserved_mwh"]:g}']:
        assert phrase in summary.data.body,'summary does not match result package'
    return dict(outcome='pass',input_sha256=payload['input_sha256'],objects=len(ids),
                isolated_water_curves=len(curves),frames=checks)
