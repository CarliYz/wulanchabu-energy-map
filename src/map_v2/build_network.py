"""Construct separate candidate water routes; keep original route untouched."""
import json
network=col('05 供回水管网 | 候选')
history=col('历史种子线 | 关闭显示',network)
history.hide_render=True; history.hide_viewport=True
for f in GEO['features']:
    if f['type']=='LineString':
        o=pipe(f['id']+' | original geometry',f['xyz'],1,steel,history)
        o['source_feature_id']=f['id']; o['unchanged_legacy_geometry']=True

routes=[]
hub=bpy.data.objects['HUB_011']
sourcecolor=mat('源侧回水 | 青灰',(.03,.36,.44),.3,.4)
orange=mat('P1近端供水 | 橙',(.97,.40,.035),.2,.45)


def closest(points,target):
    best=points[0]; distance=float('inf')
    for p in points:
        d=(p[0]-target[0])**2+(p[1]-target[1])**2
        if d<distance: best,distance=p,d
    return best


def worldport(obj,key):
    return tuple(obj.matrix_world @ Vector(obj[key]))


def sample_path(points,step=35):
    result=[]
    for a,b in zip(points[:-1],points[1:]):
        a,b=Vector(a),Vector(b)
        n=max(1,int((b-a).length/step))
        for i in range(n):
            p=a.lerp(b,i/n); result.append((p.x,p.y,ground(p.x,p.y)+5))
    p=points[-1]; result.append((p[0],p[1],ground(p[0],p[1])+5))
    return result


def offset_path(points,offset):
    result=[]
    for i,p in enumerate(points):
        a=Vector(points[max(0,i-1)][:2]); b=Vector(points[min(len(points)-1,i+1)][:2])
        d=b-a
        if d.length: d.normalize()
        x,y=p[0]-d.y*offset,p[1]+d.x*offset
        result.append((x,y,ground(x,y)+5))
    return result


def route(name,points,start,end,color,phase,from_id,to_id,radius=3,dashed=False,circuit='user_water'):
    # Fine geometry in equipment views; overview has a separate emphasis layer.
    radius=min(radius,.65)
    sampled=sample_path(points)
    sampled[0]=tuple(start); sampled[-1]=tuple(end)
    length=sum((Vector(b)-Vector(a)).length for a,b in zip(sampled[:-1],sampled[1:]))
    if dashed:
        for k in range(0,len(sampled)-1,4):
            segment=sampled[k:min(k+3,len(sampled))]
            if len(segment)>1:
                o=pipe(name+' | 后续候选段',segment,radius,color,network)
                o['route_id']=name; o['circuit']=circuit; o['phase']=phase
    else:
        o=pipe(name,sampled,radius,color,network)
        o['route_id']=name; o['circuit']=circuit; o['phase']=phase
        o['status']='candidate_unverified_not_operating'; o['display_radius_m']=radius
    reverse='RETURN' in name
    routes.append({'route_id':name,'geometry_start_node':from_id,'geometry_end_node':to_id,
                   'flow_from':to_id if reverse else from_id,'flow_to':from_id if reverse else to_id,'phase':phase,'circuit':circuit,
                   'geometry_length_m':length,'start_xyz':list(start),'end_xyz':list(end),
                   'display_radius_m':radius,'radius_is_engineering_dimension':False,
                   'dashed_future_candidate':dashed,'sampled_xyz':sampled})
    return sampled


# Main P2 route is a NEW candidate; avoid claiming that the old power plant
# endpoint is an approved urban connection. Original nine-point line is retained.
legacy=features['PIPE_P2_SEED']['xyz']
city=DESIGN_NODES['city_candidate_xyz']
center=DESIGN_NODES['main_candidate_xyz']
sup=offset_path(center,9); ret=offset_path(center,-9)
start_s=worldport(hub,'port_P2_supply_local'); start_r=worldport(hub,'port_P2_return_local')
end_s=(city[0]+9,city[1],ground(city[0]+9,city[1])+3)
end_r=(city[0]-9,city[1],ground(city[0]-9,city[1])+3)
main_s=route('P2_V2_SUPPLY',sup,start_s,end_s,red,'P2_candidate','HUB_011','CITY_INTERFACE_V2',4.5)
main_r=route('P2_V2_RETURN',ret,start_r,end_r,blue,'P2_candidate','HUB_011','CITY_INTERFACE_V2',4.5)
o=box('CITY_INTERFACE_V2',(0,0,0),(65,40,16),white,network,bevel=1)
o.location=(city[0],city[1],ground(*city[:2])+8)
o['status']='new_design_candidate_unverified_not_signed'; o['design_lonlat']=DESIGN_NODES['city_candidate_lonlat']
o['reason']='Separate candidate user node within historical new-area polygon; not the old coal plant endpoint'

# Each user receives a separate HX station, a distinct water circuit and inlet pair.
user_specs=[('AGRI_014',240,195,(-84.5,-40,1)),('AGRI_015',180,115,(-42,42,2)),
            ('AGRI_016',250,220,(-99,-57.5,1)),('AGRI_017',190,155,(-66.5,-44.5,1)),
            ('AGRI_018',190,150,(-71.5,-40,1)),('DRY_019',190,155,(2,-45,1))]
for fid,w,l,internal in user_specs:
    user=bpy.data.objects[fid]; cc=next(iter(user.users_collection))
    sx,sy=-w/2+11,-l/2+15
    box(fid+' 用户隔离换热站',(sx,sy,3.5),(14,13,7),turquoise,cc,user,.5)
    user['port_supply_local']=[sx-7,sy+2,3]
    user['port_return_local']=[sx-7,sy-2,3]
    us=worldport(user,'port_supply_local'); ur=worldport(user,'port_return_local')
    inside=(internal[0],internal[1],internal[2])
    pipe(fid+' 末端供水',[(sx+7,sy+2,3),(internal[0],sy+2,3),inside],.35,red,cc,user)
    pipe(fid+' 末端回水',[(sx+7,sy-2,2),(internal[0]-1.5,sy-2,2),(internal[0]-1.5,internal[1],1)],.35,blue,cc,user)
    future=fid in ('AGRI_018','DRY_019')
    if fid in ('AGRI_014','AGRI_015'):
        ss=worldport(hub,'port_P1_supply_local'); sr=worldport(hub,'port_P1_return_local')
        phase='P1_candidate'; color=orange
        # The direct supply loop is independent of the P2 mainline.
        path_s=[ss,(ss[0]+160,ss[1]+120,0),(us[0]-40,us[1],0),us]
        path_r=[sr,(sr[0]+168,sr[1]+120,0),(ur[0]-48,ur[1],0),ur]
    else:
        ss=closest(main_s,us)
        sr=closest(main_r,ur)
        phase='future_candidate' if future else 'P2_candidate'; color=red
        path_s=[ss,(us[0]-40,ss[1],0),(us[0]-40,us[1],0),us]
        path_r=[sr,(ur[0]-48,sr[1],0),(ur[0]-48,ur[1],0),ur]
    route(fid+'_SUPPLY',path_s,ss,us,color,phase,'HUB_011' if phase=='P1_candidate' else 'P2_V2_SUPPLY',fid,2.1,future)
    route(fid+'_RETURN',path_r,sr,ur,blue,phase,'HUB_011' if phase=='P1_candidate' else 'P2_V2_RETURN',fid,2.1,future)

# Source water remains a different water loop, with isolating interfaces.
for i,fid in enumerate(('DC_004','DC_005','DC_006')):
    source=bpy.data.objects[fid]
    source['port_supply_local']=[106,-50,4]; source['port_return_local']=[106,-62,3]
    ss=worldport(source,'port_supply_local'); sr=worldport(source,'port_return_local')
    hs=worldport(hub,'port_source_in_local'); hr=worldport(hub,'port_source_out_local')
    corridor=max(bpy.data.objects[n].location.x+235/2 for n in ('DC_004','DC_005','DC_006'))+220+i*16
    path_s=[ss,(ss[0]+80,ss[1],0),(ss[0]+80,ss[1]-70,0),(corridor,ss[1]-70,0),(corridor,hs[1]-220,0),(hs[0]+70,hs[1]-220,0),hs]
    path_r=[sr,(sr[0]+88,sr[1],0),(sr[0]+88,sr[1]-78,0),(corridor+12,sr[1]-78,0),(corridor+12,hr[1]-232,0),(hr[0]+82,hr[1]-232,0),hr]
    route(fid+'_SOURCE',path_s,ss,hs,turquoise,'source_candidate',fid,'HUB_011',2.5,circuit='source_water')
    route(fid+'_SOURCE_RETURN',path_r,sr,hr,sourcecolor,'source_candidate',fid,'HUB_011',2.5,circuit='source_water')

# Independent PTES charge/discharge branch. No duplicated heat accounting implied.
store=bpy.data.objects['STORE_012']
for suffix,startkey,endkey,color in [('CHARGE','port_P2_supply_local','port_supply_local',red),('RETURN','port_P2_return_local','port_return_local',blue)]:
    a=worldport(hub,startkey); b=worldport(store,endkey)
    route('PTES_'+suffix,[a,(b[0]+80,a[1]+120,0),(b[0]+80,b[1],0),b],a,b,color,'storage_candidate','HUB_011','STORE_012',2.5)

# Close the source-side and user-side headers inside the station.
hc=next(iter(hub.users_collection))
pipe('源侧隔离后二次供水',[(78,-22,4),(-61,-22,4),(-61,20,5)],.5,turquoise,hc,hub)
pipe('源侧隔离后二次回水',[(78,-40,3),(-68,-40,3),(-68,24,4)],.5,sourcecolor,hc,hub)
pipe('P2用户回水总管',[(45,64,2),(64,64,2),(64,-15,2)],.65,blue,hc,hub)
for yy in (-8,20):
    pipe('蒸发器源水连接',[(-61,yy,5),(-55,yy,5)],.5,turquoise,hc,hub)
    pipe('蒸发器源回水连接',[(-42,yy+4,5),(-68,yy+4,5),(-68,yy+4,4)],.5,sourcecolor,hc,hub)
    pipe('气冷器用户回水连接',[(64,yy-5,2),(24,yy-5,2),(24,yy-5,7)],.55,blue,hc,hub)

scene['route_revision']='candidate-v2; legacy geometry preserved separately'
scene['main_pipe_rendering']='Display radii exaggerated; +5m terrain display lift; not surveyed pipe sizes or burial depth'
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'/checkpoints/map-v2/03-network.blend')
print('ROUTES_JSON:'+json.dumps({'revision':'candidate-v2','routes':routes,'crossings_status':'not_surveyed; all paths schematic; road/rail/water crossings require review','original_route_preserved':True}))
