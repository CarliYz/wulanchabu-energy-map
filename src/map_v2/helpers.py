"""Shared safe-mode Blender construction helpers; no filesystem operations."""
import bpy
import math
from mathutils import Vector

ROOT='/path/to/wulanchabu-energy-map'
scene=bpy.data.scenes['01 | 地理总览']
root=bpy.data.collections['MAP_V2']
terrain=bpy.data.objects['TERRAIN | Copernicus GLO30 | actual elevations']
features={f['id']:f for f in GEO['features']}
font=bpy.data.fonts.get('STHeiti Medium')
if font is None: font=bpy.data.fonts.load('/System/Library/Fonts/STHeiti Medium.ttc')


def mat(name,color,metallic=0,roughness=.5,emission=0):
    m=bpy.data.materials.get(name)
    if m is not None: return m
    m=bpy.data.materials.new(name); m.use_nodes=True; m.diffuse_color=(*color,1)
    p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Metallic'].default_value=metallic
    p.inputs['Roughness'].default_value=roughness
    p.inputs['Emission Color'].default_value=(*color,1)
    p.inputs['Emission Strength'].default_value=emission
    return m


steel=mat('结构 | 镀锌钢',(.57,.65,.68),.65,.3)
white=mat('建筑 | 暖白',(.85,.86,.79),.1,.6)
roofmat=mat('屋面 | 石墨灰',(.13,.20,.23),.35,.55)
soil=mat('地块 | 棕土',(.24,.14,.075),roughness=.95)
slab=mat('场坪 | 混凝土',(.43,.46,.44),roughness=.95)
leaf=mat('叶菜 | 绿色',(.16,.42,.08),roughness=.78)
leaf2=mat('作物 | 深绿',(.07,.27,.065),roughness=.75)
red=mat('供水 | 红',(.84,.12,.055),.25,.35)
blue=mat('回水 | 蓝',(.045,.35,.73),.3,.35)
turquoise=mat('源侧水 | 青',(.04,.6,.64),.3,.35)
purple=mat('CO2 | 紫',(.54,.16,.75),.4,.32)
gold=mat('电与谷物 | 金',(.94,.62,.12),.2,.5)
dark=mat('标字 | 深蓝灰',(.025,.06,.075),roughness=.9,emission=.4)
glass=mat('温室 | 透明青玻璃',(.58,.82,.82),.05,.18)
gp=next(n for n in glass.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
gp.inputs['Transmission Weight'].default_value=.68
gp.inputs['IOR'].default_value=1.45


def col(name,parent=None):
    c=bpy.data.collections.get(name)
    if c is None:
        c=bpy.data.collections.new(name); (parent or root).children.link(c)
    return c


def mesh(name,vertices,faces,material,collection,parent=None):
    data=bpy.data.meshes.new(name); data.from_pydata(vertices,[],faces); data.update()
    obj=bpy.data.objects.new(name,data); collection.objects.link(obj)
    if material is not None: data.materials.append(material)
    if parent is not None: obj.parent=parent
    return obj


def box(name,xyz,size,material,collection,parent=None,bevel=0):
    x,y,z=xyz; a,b,c=[s/2 for s in size]
    vs=[(x+dx*a,y+dy*b,z+dz*c) for dx,dy,dz in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
    o=mesh(name,vs,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],material,collection,parent)
    if bevel:
        m=o.modifiers.new('柔化建筑边缘','BEVEL'); m.width=bevel; m.segments=2
        o.modifiers.new('顶点法线','WEIGHTED_NORMAL')
    return o


def rod(name,a,b,r,material,collection,parent=None,n=10):
    a,b=Vector(a),Vector(b); axis=(b-a).normalized()
    u=axis.cross(Vector((0,0,1)))
    if u.length<.01: u=axis.cross(Vector((1,0,0)))
    u.normalize(); v=axis.cross(u).normalized()
    vs=[]
    for c in (a,b):
        for i in range(n):
            off=r*(math.cos(i*2*math.pi/n)*u+math.sin(i*2*math.pi/n)*v)
            vs.append(tuple(c+off))
    fs=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]
    fs.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n))
    o=mesh(name,vs,fs,material,collection,parent)
    for p in o.data.polygons[2:]: p.use_smooth=True
    return o


def pipe(name,points,r,material,collection,parent=None):
    data=bpy.data.curves.new(name,'CURVE'); data.dimensions='3D'
    data.bevel_depth=r; data.bevel_resolution=2; data.resolution_u=1
    s=data.splines.new('POLY'); s.points.add(len(points)-1)
    for v,p in zip(s.points,points): v.co=(*p,1)
    o=bpy.data.objects.new(name,data); collection.objects.link(o); data.materials.append(material)
    if parent is not None: o.parent=parent
    return o


def text(name,body,xyz,size,material,collection,parent=None,rotation=(0,0,0)):
    d=bpy.data.curves.new(name,'FONT'); d.body=body; d.font=font; d.size=size; d.extrude=0
    o=bpy.data.objects.new(name,d); collection.objects.link(o); o.location=xyz; o.rotation_euler=rotation
    d.materials.append(material)
    if parent is not None: o.parent=parent
    return o


def ground(x,y):
    ok,hit,normal,index=terrain.ray_cast((x,y,5000),(0,0,-1))
    assert ok, ('outside DEM',x,y)
    return hit.z


def site(fid,title,width,length,collection):
    assert bpy.data.objects.get(fid) is None, ('site already exists',fid)
    x,y,z=features[fid]['xyz']
    # Interior high spots matter on a real DEM, not only the five corners.
    samples=[ground(x-width/2+width*i/max(1,int(width/10)),
                    y-length/2+length*j/max(1,int(length/10)))
             for i in range(max(1,int(width/10))+1)
             for j in range(max(1,int(length/10))+1)]
    level=max(samples)+.5
    o=bpy.data.objects.new(fid,None); collection.objects.link(o); o.location=(x,y,level)
    o['asset_id']=fid; o['source_feature_id']=fid; o['use']=title
    o['status']='拟建/待核；代表性设施模型，非实测建筑'
    o['seed_lonlat_unverified']=True; o['pad_raise_m']=level-z
    h=max(1,level-min(samples))
    box(fid+' | 场坪',(0,0,-h/2),(width,length,h),slab,collection,o)
    return o


def roof(name,cx,cy,w,l,eave,ridge,material,collection,parent):
    vs=[(cx-w/2,cy-l/2,eave),(cx,cy-l/2,ridge),(cx+w/2,cy-l/2,eave),
        (cx-w/2,cy+l/2,eave),(cx,cy+l/2,ridge),(cx+w/2,cy+l/2,eave)]
    return mesh(name,vs,[(0,3,4,1),(1,4,5,2),(0,1,2),(3,5,4)],material,collection,parent)


def plant_mesh():
    d=bpy.data.meshes.get('作物叶片实例')
    if d: return d
    vs=[(0,0,0),(0,0,1),(1,0,.45),(0,1,.45),(-1,0,.45),(0,-1,.45)]
    fs=[(0,2,1),(0,3,1),(0,4,1),(0,5,1),(0,2,3),(0,3,4),(0,4,5),(0,5,2)]
    d=bpy.data.meshes.new('作物叶片实例'); d.from_pydata(vs,[],fs); d.materials.append(leaf)
    return d


def plant(name,xyz,scale,collection,parent):
    o=bpy.data.objects.new(name,plant_mesh()); collection.objects.link(o); o.parent=parent; o.location=xyz; o.scale=scale
    return o


def greenhouse(parent,collection,cx,cy,spans,length,kind):
    w=spans*9; eave=6 if kind=='strawberry' else 8; ridge=eave+3
    box(kind+' | 种植地坪',(cx,cy,.08),(w,length,.16),soil,collection,parent)
    for i in range(spans):
        x=cx-w/2+4.5+i*9
        # Rear roof retained; foreground cut away to expose crop-specific interiors.
        roof(kind+' | 玻璃屋面',x,cy+length*.2,9,length*.6,eave,ridge,glass,collection,parent)
    frames=max(3,int(length/16))
    for j in range(frames+1):
        y=cy-length/2+length*j/frames
        for i in range(spans+1):
            x=cx-w/2+i*9
            rod('温室立柱',(x,y,0),(x,y,eave),.16,steel,collection,parent,n=6)
        for i in range(spans):
            x=cx-w/2+i*9
            pipe('温室屋架',[(x,y,eave),(x+4.5,y,ridge),(x+9,y,eave)],.16,steel,collection,parent)
    for i in range(spans*2):
        x=cx-w/2+2.2+i*4.5
        if kind=='strawberry':
            box('草莓高架槽',(x,cy,1.5),(1.5,length-5,.45),white,collection,parent)
            for y in range(int(cy-length/2+6),int(cy+length/2-4),10):
                plant('草莓冠层',(x,y,1.75),(.9,1,.55),collection,parent)
                rod('草莓果实',(x+.6,y,1.5),(x+.6,y,1.8),.28,red,collection,parent,n=6)
        elif kind=='tomato':
            box('番茄栽培槽',(x,cy,.5),(1,length-5,.6),white,collection,parent)
            for y in range(int(cy-length/2+7),int(cy+length/2-4),12):
                rod('番茄吊蔓',(x,y,.8),(x,y,4.5),.09,steel,collection,parent,n=5)
                plant('番茄植株',(x,y,.8),(1.1,1.1,3.3),collection,parent)
                rod('番茄果串',(x+.65,y,2),(x+.65,y,2.6),.3,red,collection,parent,n=6)
        elif kind=='leaf':
            box('水培槽',(x,cy,1),(2.6,length-5,.5),white,collection,parent)
            for y in range(int(cy-length/2+5),int(cy+length/2-3),7):
                plant('叶菜苗盘',(x,y,1.3),(1,1,.55),collection,parent)
        else:
            box('种薯苗床',(x,cy,.7),(2.4,length-5,.4),white,collection,parent)
            for y in range(int(cy-length/2+5),int(cy+length/2-3),8):
                plant('脱毒种薯苗',(x,y,.9),(.9,1,.9),collection,parent)
    pipe('温室供水',[(cx-w/2-2,cy-length/2,1),(cx+w/2+2,cy-length/2,1)],.28,red,collection,parent)
    pipe('温室回水',[(cx-w/2-2,cy-length/2-1.5,1),(cx+w/2+2,cy-length/2-1.5,1)],.28,blue,collection,parent)
