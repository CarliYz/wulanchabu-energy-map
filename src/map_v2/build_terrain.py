"""Run in live Blender; GEO literal is prepended by the caller."""
import bpy
import math
from mathutils import Vector

ROOT = '/path/to/wulanchabu-energy-map'
assert 'MAP_V2' not in bpy.data.collections, 'Inspect existing build before rebuilding'
scene = bpy.data.scenes.new('01 | 地理总览')
bpy.context.window.scene = scene
scene['requirement_revision'] = 'map-design-v2'
scene['CRS'] = GEO['crs']
scene['origin_utm_e_n_h'] = GEO['origin']
scene['height_multiplier'] = 1.0
scene['position_status'] = '拟建候选；历史坐标待核；非施工图'
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1
root = bpy.data.collections.new('MAP_V2')
scene.collection.children.link(root)


def collection(name):
    c = bpy.data.collections.new(name)
    root.children.link(c)
    return c


terrain_col = collection('01 DEM真实地形 | 1x')
zones_col = collection('02 规划分区 | 待核')
energy_col = collection('03 能源设备 | 拟建')
agri_col = collection('04 农业设施 | 代表模型')
network_col = collection('05 供回水管网 | 候选')
context_col = collection('06 背景与标尺')
camera_col = collection('07 地理相机')
label_col = collection('08 总览标签')


def link(obj, col):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    col.objects.link(obj)
    return obj


def material(name, color, metallic=0, roughness=.5, emission=0):
    m=bpy.data.materials.new(name)
    m.diffuse_color=(*color,1)
    m.use_nodes=True
    n=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    n.inputs['Base Color'].default_value=(*color,1)
    n.inputs['Metallic'].default_value=metallic
    n.inputs['Roughness'].default_value=roughness
    n.inputs['Emission Color'].default_value=(*color,1)
    n.inputs['Emission Strength'].default_value=emission
    return m


def line(name, points, radius, mat, col):
    c=bpy.data.curves.new(name,'CURVE'); c.dimensions='3D'
    c.resolution_u=1; c.bevel_depth=radius; c.bevel_resolution=2
    s=c.splines.new('POLY'); s.points.add(len(points)-1)
    for p,v in zip(s.points,points): p.co=(*v,1)
    o=bpy.data.objects.new(name,c); col.objects.link(o)
    o.data.materials.append(mat)
    return o


def ground(x,y):
    ok,hit,normal,index=terrain.ray_cast((x,y,5000),(0,0,-1))
    assert ok, ('Outside DEM',x,y)
    return hit.z


def camera(name, pos, target, scale):
    d=bpy.data.cameras.new(name); o=bpy.data.objects.new(name,d); camera_col.objects.link(o)
    o.location=pos; o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
    d.type='ORTHO'; d.ortho_scale=scale; d.clip_start=1; d.clip_end=100000
    return o


bpy.ops.wm.ply_import(filepath=ROOT+'/outputs/map-v2/terrain.ply')
terrain=link(bpy.context.object,terrain_col)
terrain.name='TERRAIN | Copernicus GLO30 | actual elevations'
terrain['height_range_m']=GEO['height_range_m']
terrain['source']='Copernicus DEM 2021 release GLO-30; EGM2008; 40m display mesh'
terrain['height_multiplier']=1.0
terrain['not_surveyed_ground']=True
for p in terrain.data.polygons: p.use_smooth=True
bounds=GEO['utm_bounds']; origin=GEO['origin']
xmin,ymin=bounds[0]-origin[0],bounds[1]-origin[1]
xmax,ymax=bounds[2]-origin[0],bounds[3]-origin[1]
uv=terrain.data.uv_layers.new(name='UTM satellite registration')
uvdata=[]
for loop in terrain.data.loops:
    v=terrain.data.vertices[loop.vertex_index].co
    uvdata.extend(((v.x-xmin)/(xmax-xmin),(v.y-ymin)/(ymax-ymin)))
uv.data.foreach_set('uv',uvdata)
mat=material('EOxCloudless Sentinel-2 2024 | CC BY-NC-SA 4.0',(.5,.5,.5),roughness=.95)
nodes=mat.node_tree.nodes
tex=nodes.new('ShaderNodeTexImage'); tex.image=bpy.data.images.load(ROOT+'/outputs/map-v2/satellite-utm49n.jpg')
tex.image.pack()
bsdf=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
mat.node_tree.links.new(tex.outputs['Color'],bsdf.inputs['Base Color'])
terrain.data.materials.append(mat)
terrain['imagery_attribution']='EOxCloudless by EOX IT Services GmbH; contains modified Copernicus Sentinel data 2024; CC BY-NC-SA 4.0; reprojected to UTM49N'
terrain['imagery_is_google']=False
palette=[(.96,.59,.12),(.11,.72,.58),(.26,.50,.94)]
for f in GEO['features']:
    if f['id'] not in ('ZONE_AGRIA','ZONE_AGRIB','ZONE_AGRIC'): continue
    idx=['ZONE_AGRIA','ZONE_AGRIB','ZONE_AGRIC'].index(f['id'])
    points=[]
    coords=f['xyz'][0]
    for a,b in zip(coords[:-1],coords[1:]):
        count=max(2,int((Vector(b[:2])-Vector(a[:2])).length/45))
        for i in range(count):
            t=i/count; x=a[0]*(1-t)+b[0]*t; y=a[1]*(1-t)+b[1]*t
            points.append((x,y,ground(x,y)+5))
    points.append(points[0])
    o=line(f['id']+' | planning outline',points,5,material('分区 '+str(idx+1),palette[idx],emission=.15),zones_col)
    o['source_feature_id']=f['id']; o['geometry_status']='schematic_unverified_not_cadastral'
cx,cy=(xmin+xmax)/2,(ymin+ymax)/2
cam=camera('CAM_01 区域总览',(cx,cy-19500,24500),(cx,cy,60),28500)
scene.camera=cam
world=bpy.data.worlds.new('地图自然光'); world.use_nodes=True
background=next(n for n in world.node_tree.nodes if n.type=='BACKGROUND')
background.inputs['Color'].default_value=(.7,.8,1,1)
background.inputs['Strength'].default_value=.55
scene.world=world
sun_data=bpy.data.lights.new('地理日光','SUN'); sun_data.energy=2.4; sun_data.angle=.15
sun=bpy.data.objects.new('地理日光',sun_data); context_col.objects.link(sun)
sun.rotation_euler=(math.radians(25),math.radians(-25),math.radians(-35))
scene.render.engine=bpy.data.scenes['Scene'].render.engine
scene.render.resolution_x=1920; scene.render.resolution_y=1440; scene.render.resolution_percentage=100
scene.view_settings.view_transform='Standard'
scene.view_settings.look='None'
scene.render.image_settings.file_format='PNG'
scene.render.film_transparent=False
for a in bpy.context.screen.areas:
    if a.type=='VIEW_3D':
        a.spaces.active.region_3d.view_perspective='CAMERA'
        a.spaces.active.clip_end=100000
        a.spaces.active.shading.type='MATERIAL'
        a.spaces.active.overlay.show_overlays=False
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'/checkpoints/map-v2/01-terrain-and-zones.blend')
print({'stage':'M2','scene':scene.name,'terrain_vertices':len(terrain.data.vertices),'elevation_m':GEO['height_range_m'],'objects':len(scene.objects),'saved':'01-terrain-and-zones.blend'})
