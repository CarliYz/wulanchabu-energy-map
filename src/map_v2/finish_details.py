"""Final readability and interface checks. GEO + helpers are prepended."""
network=bpy.data.collections['05 供回水管网 | 候选']
for o in network.objects:
    if o.type=='CURVE' and 'route_id' in o:
        o.data.bevel_depth=.65
        o['display_radius_m']=.65

# Bring the final pads to the same safe level when rebuilding, including interior
# high spots. They remain schematic engineered pads above the unchanged DEM.
for p in [o for o in scene.objects if 'asset_id' in o]:
    pad=bpy.data.objects[p.name+' | 场坪']
    xs=[v.co.x for v in pad.data.vertices]; ys=[v.co.y for v in pad.data.vertices]
    lo,hi=min(xs),max(xs); bottom,top=min(ys),max(ys)
    nx=max(1,int((hi-lo)/8)); ny=max(1,int((top-bottom)/8))
    samples=[ground(p.location.x+lo+(hi-lo)*i/nx,p.location.y+bottom+(top-bottom)*j/ny) for i in range(nx+1) for j in range(ny+1)]
    # Current network ports already refer to this plane, so guard rather than move.
    assert p.location.z >= max(samples)+.3, ('Pad intersects DEM',p.name)

# Explicit labels identify the four pieces in the geographic station close-up.
hs=bpy.data.scenes['02 | 热泵枢纽']; hc=bpy.data.collections['HUD | '+hs.name]
camera=hs.camera; hub=bpy.data.objects['HUB_011']
bpy.context.window.scene=hs; bpy.context.view_layer.update()
w=camera.data.ortho_scale; h=w*hs.render.resolution_y/hs.render.resolution_x
def emitmat(name,color):
    m=bpy.data.materials.new(name); m.use_nodes=True; ns=m.node_tree.nodes; ns.clear()
    e=ns.new('ShaderNodeEmission'); e.inputs['Color'].default_value=(*color,1)
    out=ns.new('ShaderNodeOutputMaterial'); m.node_tree.links.new(e.outputs[0],out.inputs[0])
    return m
paper=bpy.data.materials['界面 | 米白']; ink=bpy.data.materials['界面 | 墨色']
labelspecs=[('1 蒸发器',(-42,-8,10),-.47,'源侧水 | 青'),('2 压缩机',(-10,-8,12),-.23,'CO2 | 紫'),('3 气冷器',(24,-8,10),.01,'供水 | 红'),('4 节流阀',(0,-17,3),.25,'CO2 | 紫')]
for title,local,xfrac,colorname in labelspecs:
    target=camera.matrix_world.inverted() @ (hub.matrix_world @ Vector(local))
    x=w*xfrac; y=-h*.31
    box('部件标牌 '+title,(x+w*.105,y,-21),(w*.22,h*.05,.01),paper,hc,camera)
    text('部件名称 '+title,title,(x+w*.008,y-h*.008,-19),w*.013,ink,hc,camera)
    color=bpy.data.materials[colorname]
    pipe('部件定位线 '+title,[(target.x,target.y,-20),(target.x,y+h*.035,-20),(x+w*.105,y+h*.035,-20),(x+w*.105,y+h*.025,-20)],w*.00065,color,hc,camera)

# Static flow arrowheads are geometry, no animation or performance claims.
def arrow3d(name,tip,direction,length,radius,color,collection,parent=None):
    tip=Vector(tip); axis=Vector(direction).normalized(); base=tip-axis*length
    u=axis.cross(Vector((0,0,1)))
    if u.length<.01: u=axis.cross(Vector((1,0,0)))
    u.normalize(); v=axis.cross(u)
    vs=[tuple(tip)]+[tuple(base+radius*(math.cos(i*2*math.pi/12)*u+math.sin(i*2*math.pi/12)*v)) for i in range(12)]
    fs=[(0,1+i,1+(i+1)%12) for i in range(12)]
    fs.append(tuple(range(12,0,-1)))
    return mesh(name,vs,fs,color,collection,parent)
ec=next(iter(hub.users_collection))
for yy in (-8,20):
    for tip,axis in [((5,yy,15),(1,0,0)),((24,yy-9,8),(0,0,-1)),((8,yy-9,2),(-1,0,0)),((-42,yy-3,2),(0,1,0))]:
        arrow3d('CO2循环静态流向',tip,axis,2.3,1.1,purple,ec,hub)
display=bpy.data.collections['09 总览管线强调 | 非真实管径']
for name,sign,color in [('MAP_DISPLAY | P2_V2_SUPPLY',1,red),('MAP_DISPLAY | P2_V2_RETURN',-1,blue)]:
    o=bpy.data.objects[name]; points=o.data.splines[0].points
    for fraction in (.24,.5,.76):
        i=int((len(points)-2)*fraction)
        p=Vector(points[i].co[:3]); q=Vector(points[i+sign].co[:3])
        arrow3d('总览供回水流向',p+Vector((0,0,12)),q-p,110,42,color,display)
bpy.context.window.scene=scene
bpy.context.view_layer.update()
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'/outputs/map-v2/乌兰察布_真实地理场景_v2.blend')
print('Final detail geometry, station labels and static flow arrows saved')
