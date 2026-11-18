"""Blender presentation builder. Receives frozen results; never solves dispatch."""
import bpy
import math
from mathutils import Vector

PREFIX = 'ENERGY_'
FONT_PATH = '/System/Library/Fonts/STHeiti Medium.ttc'


def build(payload, phase=3):
    scene = bpy.data.scenes.get('ENERGY_MVP') or bpy.data.scenes.new('ENERGY_MVP')
    if bpy.context.window:
        bpy.context.window.scene = scene
    scene.animation_data_clear()
    old = bpy.data.collections.get('ENERGY_GENERATED')
    if old:
        for obj in list(old.all_objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(old)
    collection = bpy.data.collections.new('ENERGY_GENERATED')
    scene.collection.children.link(collection)
    scene['requirement_revision'] = payload['requirement_revision']
    scene['design_revision'] = payload['design_revision']
    scene['input_sha256'] = payload['input_sha256']
    scene['result_basis'] = 'synthetic_teaching_not_local'
    scene['geographic_status'] = 'original_schematic_not_local_reconstruction'
    scene['phase'] = phase
    scene.unit_settings.system = 'METRIC'

    def register(obj, name, material=None):
        obj.name = PREFIX+name
        obj['object_id'] = name
        obj['evidence'] = 'conceptual_original_not_local_asset'
        for c in list(obj.users_collection):
            c.objects.unlink(obj)
        collection.objects.link(obj)
        if material:
            obj.data.materials.clear(); obj.data.materials.append(material)
        return obj

    def mat(name, color, metallic=0, emission=0, alpha=1):
        m = bpy.data.materials.get(PREFIX+name) or bpy.data.materials.new(PREFIX+name)
        m.use_nodes=True
        n=m.node_tree.nodes.get('Principled BSDF')
        n.inputs['Base Color'].default_value=(*color, alpha)
        n.inputs['Metallic'].default_value=metallic
        n.inputs['Roughness'].default_value=.36
        n.inputs['Alpha'].default_value=alpha
        n.inputs['Emission Color'].default_value=(*color,1)
        n.inputs['Emission Strength'].default_value=emission
        m.diffuse_color=(*color,alpha)
        return m

    navy=mat('Navy',(.021,.045,.077),.3)
    ground=mat('Ground',(.009,.017,.030))
    cream=mat('Foundation',(.35,.31,.23))
    white=mat('Porcelain',(.68,.76,.78),.25)
    metal=mat('Steel',(.30,.42,.47),.85)
    hot=mat('Supply',(.72,.055,.025),.35,.6)
    blue=mat('Return',(.025,.20,.68),.35,.6)
    gold=mat('Electric',(.95,.50,.055),.6,.6)
    green=mat('Plants',(.07,.25,.13))
    glass=mat('Greenhouse',(.18,.45,.42),.2,0,.18)
    glow=mat('Text',(.77,.86,.85),0,1)
    muted=mat('MutedText',(.48,.61,.67),0,1)
    warmtext=mat('WarmText',(.98,.46,.15),0,1)
    palegold=mat('WarmFill',(.7,.24,.045),.4,.4)

    def box(name,loc,dims,material,bevel=.04):
        bpy.ops.mesh.primitive_cube_add(size=1,location=loc)
        o=register(bpy.context.object,name,material); o.scale=dims
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        if bevel:
            mod=o.modifiers.new('Edge finish','BEVEL');mod.width=bevel;mod.segments=3
            o.modifiers.new('Weighted normals','WEIGHTED_NORMAL')
        return o

    def cylinder(name,loc,radius,depth,material):
        bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=radius,depth=depth,location=loc)
        o=register(bpy.context.object,name,material)
        mod=o.modifiers.new('Edge finish','BEVEL');mod.width=.035;mod.segments=2
        return o

    def pipe(name,points,material,radius=.065):
        data=bpy.data.curves.new(PREFIX+name,'CURVE');data.dimensions='3D'
        data.bevel_depth=radius;data.bevel_resolution=3
        spline=data.splines.new('POLY');spline.points.add(len(points)-1)
        for p,xyz in zip(spline.points,points):p.co=(*xyz,1)
        o=bpy.data.objects.new(PREFIX+name,data);collection.objects.link(o)
        o['object_id']=name;o['geometry_status']='schematic_not_route_or_pipe_design'
        data.materials.append(material)
        return o

    font=bpy.data.fonts.get('Energy Chinese')
    if not font:
        font=bpy.data.fonts.load(FONT_PATH);font.name='Energy Chinese'

    def text(name,body,loc,size,material=glow,rotation=None):
        data=bpy.data.curves.new(PREFIX+name,'FONT');data.body=body;data.font=font
        data.size=size;data.align_y='CENTER';data.extrude=0
        o=bpy.data.objects.new(PREFIX+name,data);collection.objects.link(o)
        o['object_id']=name;o.location=loc;data.materials.append(material)
        if rotation:o.rotation_euler=rotation
        return o

    box('Stage',(0,1,-.48),(25,15,.8),navy,.35)
    box('Stage_inset',(0,1,-.02),(24.3,14.3,.12),cream,.18)
    box('Backdrop',(0,0,-1.05),(200,200,.2),ground,.02)
    for x in range(-11,13,2):
        pipe('grid_x_'+str(x),[(x,-5.7,.055),(x,7.7,.055)],metal,.007)
    for y in range(-5,9,2):
        pipe('grid_y_'+str(y),[(-11.7,y,.055),(11.7,y,.055)],metal,.007)
    for ident,x,y,w,h in [('SRC_DEMO',-7,0,5.5,4.5),('HX_DEMO',-1,0,2.7,3.3),
                           ('USER_DEMO',7,0,6.4,5.2),('TES_DEMO',2.6,5.2,4.2,4.2)]:
        o=box(ident+'.plinth',(x,y,.16),(w,h,.25),navy,.1)
        o['asset_id']=ident

    box('SRC_DEMO.body',(-7,0,1.5),(4.4,2.8,2.4),white,.12)
    box('SRC_DEMO.roof',(-7,0,2.78),(4.7,3.05,.22),navy,.08)
    for x in (-8.3,-7,-5.7):
        cylinder('SRC_DEMO.fan'+str(x),(x,0,2.99),.42,.16,metal)
        for i in range(5):
            o=box('SRC_DEMO.blade'+str(x)+'_'+str(i),(x,0,3.09),(.7,.06,.025),navy,.01)
            o.rotation_euler.z=i*math.pi/5
    for i in range(15):
        box('SRC_DEMO.vent'+str(i),(-8.7+i*.24,-1.42,1.55),(.09,.03,1.4),metal,.006)
    box('SRC_DEMO.indicator',(-7,-1.46,2.48),(3.8,.04,.06),gold,.01)

    for i in range(14):
        box('HX_DEMO.plate'+str(i),(-1.5+i*.075,0,1.45),(.045,1.65,2.1),metal if i%2 else white,.018)
    for x in (-1.7,-.3):
        box('HX_DEMO.frame'+str(x),(x,0,1.45),(.14,2.05,2.4),navy,.025)
        for y in (-.88,.88):
            cylinder('HX_DEMO.bolt'+str(x)+str(y),(x,y,2.7),.06,.3,gold)
    box('HX_DEMO.isolation',(-1,0,2.74),(.055,2.0,.12),gold,.01)

    # Open-frame greenhouse; dimensions illustrate a candidate user, not a local building.
    for i,x in enumerate([4.3+i*.67 for i in range(9)]):
        pipe('USER_DEMO.rib'+str(i),[(x,-1.9,.35),(x,-1.9,2.0),(x,0,3.35),
                                    (x,1.9,2.0),(x,1.9,.35)],white,.045)
    for y,z in [(-1.9,2),(0,3.35),(1.9,2)]:
        pipe('USER_DEMO.purlin'+str(y),[(4.3,y,z),(9.66,y,z)],metal,.04)
    for i,(y,z,angle) in enumerate([(-.95,2.675,math.atan2(1.35,1.9)),(.95,2.675,-math.atan2(1.35,1.9))]):
        o=box('USER_DEMO.roof'+str(i),(6.98,y,z),(5.36,2.33,.018),glass,0)
        o.rotation_euler.x=angle
    for y in (-1.05,0,1.05):
        box('USER_DEMO.bed'+str(y),(7,y,.50),(4.9,.62,.25),navy,.05)
        for i in range(10):
            x=4.8+i*.47
            cylinder('USER_DEMO.plant'+str(y)+'_'+str(i),(x,y,.82),.17,.35,green)

    # The fill is an energy gauge, not a simulated physical water level.
    box('TES_DEMO.bottom',(2.6,5.2,.45),(3.0,3.0,.2),metal,.08)
    for x in (1.1,4.1):
        for y in (3.7,6.7):
            box('TES_DEMO.post'+str(x)+str(y),(x,y,2.0),(.13,.13,3.0),white,.025)
    for z in (.5,1.25,2,2.75,3.5):
        pipe('TES_DEMO.ring'+str(z),[(1.1,3.7,z),(4.1,3.7,z),(4.1,6.7,z),(1.1,6.7,z),(1.1,3.7,z)],metal,.04)
    fill=box('TES_DEMO.energy_fill',(2.6,5.2,1.93),(2.65,2.65,2.65),palegold,.04)
    fill['meaning']='end-of-step energy gauge, not water volume or thermocline'
    for z,t in [(3.6,'4 MWh'),(.5,'0')]:
        text('TES_DEMO.tick'+str(z),t,(4.3,3.7,z),.25,glow,(math.pi/2,0,0))

    camera_data=bpy.data.cameras.new(PREFIX+'Camera')
    camera=bpy.data.objects.new(PREFIX+'Camera',camera_data);collection.objects.link(camera)
    camera['object_id']='Camera';camera.location=(21,-31,25)
    camera.rotation_euler=(Vector((0,1,1))-camera.location).to_track_quat('-Z','Y').to_euler()
    camera_data.type='ORTHO';camera_data.ortho_scale=33
    camera_data.lens=48;scene.camera=camera
    scene.render.engine='BLENDER_EEVEE'
    scene.eevee.taa_render_samples=32
    scene.render.resolution_x=1280;scene.render.resolution_y=720;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    scene.render.fps=12;scene.frame_start=1;scene.frame_end=432
    scene.render.film_transparent=False
    world=bpy.data.worlds.get(PREFIX+'World') or bpy.data.worlds.new(PREFIX+'World')
    world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.075,.11,.17,1)
    world.node_tree.nodes['Background'].inputs[1].default_value=.5;scene.world=world
    for name,loc,power,size,color in [('Key',(-6,-10,20),5000,12,(.75,.85,1)),
                                       ('Rim',(3,10,15),6500,10,(1,.62,.28)),
                                       ('Fill',(12,-3,10),2400,9,(.4,.7,1))]:
        data=bpy.data.lights.new(PREFIX+name,'AREA');data.energy=power;data.shape='DISK';data.size=size;data.color=color
        o=bpy.data.objects.new(PREFIX+name,data);collection.objects.link(o);o['object_id']=name;o.location=loc
        o.rotation_euler=(Vector((0,1,0))-o.location).to_track_quat('-Z','Y').to_euler()
    scene.view_settings.view_transform='AgX'

    def hud(name,body,x,y,size=.4,material=glow):
        o=text(name,body,(x,y,-1.5),size,material)
        o.parent=camera
        return o

    hud('Title','算热储  /  近端直供样机',-15,8.0,.77)
    hud('Basis','合成算例 · 非当地运行  |  设施均为概念 / 候选',-15,6.95,.36,muted)
    hud('Legend','红：供热水   蓝：回水   金：泵电',5.7,8.0,.31,muted)
    hud('Footer','温度假设满足；未建水力、分层、室温模型。管线和运动速度为示意。',-15,-8.25,.29,muted)
    hud('Location','乌兰察布位置参考  40.989458 N / 113.245406 E  ·  AWS-000760 公告第2页',-15,-7.65,.29,muted)
    hud('Geometry_note','原创拓扑台座 · 非当地实景 / GIS比例',5.7,7.25,.29,muted)

    for ident,body,loc in [('SRC_DEMO','概念源接口',(-9.3,-.6,4.2)),
                             ('HX_DEMO','隔离板换',(-2.5,.1,3.9)),
                             ('USER_DEMO','候选近端用户',(9.3,-1.8,4.4)),
                             ('TES_DEMO','概念热库',(1.2,5.2,4.4))]:
        text(ident+'.label',body,loc,.42,glow,camera.rotation_euler)

    paths={}
    if phase>=2:
        paths={
            'primary_hot':([(-4.8,-.9,1.7),(-2.4,-.9,1.7),(-1.78,-.65,1.7)],hot,'source_used'),
            'primary_return':([(-1.78,.65,.85),(-3,1.65,.85),(-4.8,1,.85)],blue,'source_used'),
            'secondary_hot':([(-.22,-.65,1.7),(1.2,-.65,1.7),(1.2,-2.7,.8),(5.4,-2.7,.8)],hot,'direct_mw'),
            'secondary_delivery':([(5.4,-2.7,.8),(6.1,-2.7,.8),(6.1,-1.9,.8)],hot,'delivered_mw'),
            'secondary_return':([(8.1,-1.9,.65),(8.1,-3.8,.65),(5.4,-3.8,.65)],blue,'delivered_mw'),
            'secondary_return_hx':([(5.4,-3.8,.65),(-.22,-3.8,.65),(-.22,.65,.85)],blue,'direct_mw'),
            'storage_charge':([(1.2,-.65,1.7),(1.2,3.7,1.4),(1.1,4.6,1.4)],hot,'charge_mw'),
            'storage_charge_return':([(1.1,5.8,1),(-.1,5.8,1),(-.1,.65,.85),(-.22,.65,.85)],blue,'charge_mw'),
            'storage_discharge':([(4.1,4.6,1.4),(5.4,4.6,1.4),(5.4,-2.7,.8),(6.1,-2.7,.8)],hot,'discharge_mw'),
            'storage_discharge_return':([(5.4,-3.8,.65),(6.4,-3.8,.65),(6.4,5.8,1),(4.1,5.8,1)],blue,'discharge_mw'),
        }
        for name,(points,m,metric) in paths.items():
            o=pipe(name,points,m)
            o['water_loop']='primary' if name.startswith('primary') else 'secondary'
            o['metric']=metric
        pipe('pump_electric',[(-7,-4.7,.7),(-3.4,-4.7,.7),(-3.4,-2.9,.7)],gold,.04)
        cylinder('PUMP_DEMO',(-3.4,-2.9,.72),.3,.55,gold)
        text('Pump_label','泵电 0.02 MW / 假设电网',(-8,-4.7,1.4),.30,gold,camera.rotation_euler)
        hud('Loop_hint','两侧水路隔离  /  热库位于用户二次侧',-15,-7.05,.32,muted)

    def visibility(o,start,end):
        for f,hidden in [(0,True),(start,False),(end+1,True)]:
            o.hide_render=hidden;o.hide_viewport=hidden
            o.keyframe_insert(data_path='hide_render',frame=f)
            o.keyframe_insert(data_path='hide_viewport',frame=f)

    lookup={(r['scenario_id'],r['hour_index']):r for r in payload['rows']}
    schedule=[(1,72,'MVP_NORMAL',0,'01  从近端开始：位置事实与概念能力分开'),
              (73,90,'MVP_NORMAL',0,'02  先供用户，再用余量充库'),
              (91,108,'MVP_NORMAL',1,'02  先供用户，再用余量充库'),
              (109,126,'MVP_NORMAL',2,'02  先供用户，再用余量充库'),
              (127,144,'MVP_NORMAL',3,'02  先供用户，再用余量充库'),
              (145,204,'MVP_NORMAL',6,'03  库满之后，余量成为弃热'),
              (205,240,'MVP_SOURCE_OUTAGE',4,'04  源退出：热库先缓冲'),
              (241,276,'MVP_SOURCE_OUTAGE',5,'04  源退出：热库逐时耗尽'),
              (277,312,'MVP_SOURCE_OUTAGE',6,'05  空库之后：未供必须显示'),
              (313,348,'MVP_SOURCE_OUTAGE',7,'05  无备用：不能把缺额画成成功'),
              (349,360,'MVP_SOURCE_OUTAGE',8,'06  源恢复：先供用户再充热'),
              (361,372,'MVP_SOURCE_OUTAGE',9,'06  源恢复：先供用户再充热'),
              (373,384,'MVP_SOURCE_OUTAGE',10,'06  源恢复：先供用户再充热'),
              (385,396,'MVP_SOURCE_OUTAGE',11,'06  源恢复：先供用户再充热'),
              (397,432,'MVP_SOURCE_OUTAGE',11,'07  验证通过的是教学逻辑，工程条件仍待核')]
    if phase<3:
        schedule=[(1,432,'MVP_NORMAL',6,'阶段检查：概念资产与隔离回路')]
    scene['timeline_json']=str([(a,b,s,t) for a,b,s,t,_ in schedule])
    for index,(start,end,scenario,t,chapter) in enumerate(schedule):
        r=lookup[(scenario,t)]
        metrics=dict(r);metrics['source_used']=r['direct_mw']+r['charge_mw']
        for key in ['source_mw','delivered_mw','unserved_mw','storage_end_mwh','charge_mw','discharge_mw','curtailed_mw']:
            scene[key]=r[key];scene.keyframe_insert(data_path='["'+key+'"]',frame=start)
        scene['hour_index']=t;scene.keyframe_insert(data_path='["hour_index"]',frame=start)
        fraction=r['storage_end_mwh']/4
        fill.scale.z=max(.001,fraction);fill.location.z=.605+1.325*fraction
        fill.keyframe_insert(data_path='scale',frame=start);fill.keyframe_insert(data_path='location',frame=start)
        status='正常' if scenario=='MVP_NORMAL' else ('未供' if r['unserved_mw'] else '源退出 / 储热缓冲' if r['source_mw']==0 else '恢复')
        blocks=[('chapter',chapter,-15,5.95,.40,glow),
                ('clock',f'合成时段 t={t:02d}  /  1h步长  /  {status}',-15,-4.95,.40,warmtext if r['unserved_mw'] else glow),
                ('power',f'源可用 {r["source_mw"]:g} MW     用户需 {r["demand_mw"]:g} MW     交付 {r["delivered_mw"]:g} MW     未供 {r["unserved_mw"]:g} MW',-15,-5.7,.47,warmtext if r['unserved_mw'] else glow),
                ('storage',f'充热 {r["charge_mw"]:g} MW   放热 {r["discharge_mw"]:g} MW   库存(时段终) {r["storage_end_mwh"]:g} / 4 MWh   弃热 {r["curtailed_mw"]:g} MW',-15,-6.42,.38,glow)]
        for suffix,body,x,y,size,m in blocks:
            o=hud('HUD_'+str(index)+'_'+suffix,body,x,y,size,m)
            o['scenario_id']=scenario;o['hour_index']=t
            for key in ['source_mw','delivered_mw','unserved_mw','storage_end_mwh']:o[key]=r[key]
            visibility(o,start,end)
        if index==len(schedule)-1 and phase>=3:
            n=payload['summary']['MVP_NORMAL'];q=payload['summary']['MVP_SOURCE_OUTAGE']
            o=hud('Summary',f'24h累计（MWh）\n正常交付 {n["delivered_mwh"]:g}\n退出交付 {q["delivered_mwh"]:g} / 未供 {q["unserved_mwh"]:g}',5.7,6.35,.36,warmtext)
            visibility(o,start,end)
        if phase>=2:
            for name,(points,m,metric) in paths.items():
                # Per-interval markers bake direction and zero-flow gating into native keyframes.
                if metrics[metric]<=0:continue
                lengths=[(Vector(b)-Vector(a)).length for a,b in zip(points,points[1:])]
                total=sum(lengths)
                for j in range(3):
                    bpy.ops.mesh.primitive_uv_sphere_add(segments=8,ring_count=4,radius=.12)
                    marker=register(bpy.context.object,'flow_'+str(index)+'_'+name+'_'+str(j),m)
                    marker['flow_metric']=metric;marker['flow_value_mw']=metrics[metric]
                    marker['scenario_id']=scenario;marker['hour_index']=t
                    visibility(marker,start,end)
                    for f in range(start,end+1):
                        distance=((j/3+(f-start)/26)%1)*total
                        for a,b,length in zip(points,points[1:],lengths):
                            if distance<=length:
                                marker.location=Vector(a).lerp(Vector(b),distance/length);break
                            distance-=length
                        marker.keyframe_insert(data_path='location',frame=f)

    # Discrete business values and visibility must not tween through outages.
    for owner in list(collection.objects)+[scene]:
        if owner.animation_data and owner.animation_data.action:
            action=owner.animation_data.action
            for layer in action.layers:
                for strip in layer.strips:
                    for bag in strip.channelbags:
                        for curve in bag.fcurves:
                            mode='LINEAR' if owner.name.startswith(PREFIX+'flow_') and curve.data_path=='location' else 'CONSTANT'
                            for point in curve.keyframe_points:point.interpolation=mode
    scene.frame_set(170 if phase>=3 else 1)
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                area.spaces.active.region_3d.view_perspective='CAMERA'
                area.spaces.active.shading.type='MATERIAL'
                area.spaces.active.overlay.show_overlays=False
    print('ENERGY_BUILD_OK',phase,'objects',len(collection.objects),'input',payload['input_sha256'])
    return scene
