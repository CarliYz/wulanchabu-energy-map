"""Create linked geographic views, source attribution, map labels and legend."""
overview=scene
cam=bpy.data.objects['CAM_01 区域总览']
cam.location=(-2000,-17000,24500)
cam.rotation_euler=(Vector((-2000,2700,130))-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.ortho_scale=15400
overview.camera=cam
display=col('09 总览管线强调 | 非真实管径')


def flatmat(name,color):
    m=bpy.data.materials.get(name)
    if m is not None: return m
    m=bpy.data.materials.new(name); m.use_nodes=True
    ns=m.node_tree.nodes; ns.clear()
    e=ns.new('ShaderNodeEmission'); e.inputs['Color'].default_value=(*color,1); e.inputs['Strength'].default_value=1
    out=ns.new('ShaderNodeOutputMaterial'); m.node_tree.links.new(e.outputs[0],out.inputs['Surface'])
    m.diffuse_color=(*color,1)
    return m


paper=flatmat('界面 | 米白',(.94,.955,.925))
ink=flatmat('界面 | 墨色',(.023,.055,.067))
muted=flatmat('界面 | 次要字',(.17,.23,.24))
accent=flatmat('界面 | 森绿',(.035,.30,.23))
colors=[flatmat('界面 | A 橙',(.86,.39,.035)),flatmat('界面 | B 绿',(.02,.48,.34)),flatmat('界面 | C 蓝',(.10,.30,.70))]

# This collection explicitly adds screen legibility; physical route data is retained.
for obj in list(bpy.data.collections['05 供回水管网 | 候选'].objects):
    if obj.type!='CURVE' or 'route_id' not in obj: continue
    d=obj.data.copy(); new=bpy.data.objects.new('MAP_DISPLAY | '+obj.name,d); display.objects.link(new)
    d.bevel_depth=13
    sign=-1 if 'RETURN' in obj['route_id'] else 1
    for spline in d.splines:
        points=[Vector(p.co[:3]) for p in spline.points]
        for i,p in enumerate(spline.points):
            tangent=points[min(i+1,len(points)-1)]-points[max(i-1,0)]
            tangent.z=0
            if tangent.length: tangent.normalize()
            p.co.x-=tangent.y*sign*18; p.co.y+=tangent.x*sign*18; p.co.z+=15
    new['display_only']=True; new['original_route_id']=obj['route_id']


def settings(s):
    s.world=overview.world; s.render.engine=overview.render.engine
    s.render.resolution_x=1920; s.render.resolution_y=1320; s.render.resolution_percentage=100
    s.render.image_settings.file_format='PNG'
    s.view_settings.view_transform='Standard'; s.view_settings.look='None'
    s.render.film_transparent=False
    if 'taa_render_samples' in s.eevee.bl_rna.properties: s.eevee.taa_render_samples=64
    s['requirement_revision']='map-design-v2'; s['shared_geographic_model']='MAP_V2'


def exclude(layercol,name):
    if layercol.name==name: layercol.exclude=True; return
    for c in layercol.children: exclude(c,name)


def hud(s,title,subtitle,footnote,overview_mode=False):
    c=bpy.data.collections.new('HUD | '+s.name); s.collection.children.link(c)
    camera=s.camera; width=camera.data.ortho_scale; height=width*s.render.resolution_y/s.render.resolution_x
    def panel(name,x,y,w,h,material):
        return box(name,(x,y,-25),(w,h,.01),material,c,camera)
    def label(body,x,y,size,material=ink):
        return text('HUD '+body[:24],body,(x,y,-24),size,material,c,camera)
    panel('标题底板',0,height*.427,width,height*.146,paper)
    label(title,-width*.47,height*.434,width*.024)
    label(subtitle,-width*.47,height*.391,width*.0095,muted)
    panel('来源底板',0,-height*.447,width,height*.106,paper)
    label(footnote,-width*.47,-height*.424,width*.010,ink)
    label('地形：Copernicus DEM GLO-30 2021 · 高程1×  |  影像：EOxCloudless / EOX · Copernicus Sentinel 2024',-width*.47,-height*.461,width*.0072,muted)
    label('影像经UTM49N配准 · CC BY-NC-SA 4.0  |  设施为拟建代表模型，历史坐标待核；管线非施工设计',-width*.47,-height*.483,width*.0072,muted)
    if overview_mode:
        panel('图例底板',-width*.331,-height*.29,width*.30,height*.16,paper)
        label('传输图例 / 候选线路',-width*.465,-height*.25,width*.011)
        label('橙：P1近端供水   红/蓝：P2供回水',-width*.465,-height*.285,width*.0084)
        label('青：源侧水   紫：站内CO₂闭环',-width*.465,-height*.317,width*.0084)
        label('虚线：C区后续候选；总览管线加粗错开展示',-width*.465,-height*.349,width*.0084)
        label('N ↑ 网格北',width*.36,height*.30,width*.012)
        pipe('1km比例尺',[(-width*.46,-height*.17,-23),(-width*.46+1000,-height*.17,-23)],width*.0016,ink,c,camera)
        label('1 km',-width*.46,-height*.155,width*.009)
    return c,width,height


settings(overview)
bpy.context.view_layer.update()
hudcol,w,h=hud(overview,'乌兰察布｜算力余热 × 设施农业','同一真实地理模型 · 源区 → A近端 → B中段 → C近城 → 城市候选接口','方案空间展示 · 不代表已建、已签约或已供热；静态模型先行',True)


def maplabel(fid,title,detail,xfrac,yfrac,color,widthfrac=.245):
    o=bpy.data.objects[fid]
    target=cam.matrix_world.inverted() @ (o.matrix_world.translation+Vector((0,0,12)))
    x,y=w*xfrac,h*yfrac; bw=w*widthfrac; bh=h*.08
    box('地图标牌 '+fid,(x+bw/2,y,-22),(bw,bh,.01),paper,hudcol,cam)
    box('地图标牌色条 '+fid,(x,y,-21),(w*.0025,bh,.01),color,hudcol,cam)
    text('地图标题 '+fid,title,(x+w*.009,y+h*.008,-20),w*.012,color,hudcol,cam)
    text('地图说明 '+fid,detail,(x+w*.009,y-h*.022,-20),w*.0082,ink,hudcol,cam)
    endpoint=(x if target.x<x else x+bw,y,-21)
    pipe('地图定位线 '+fid,[(target.x,target.y,-21),(target.x,endpoint[1],-21),endpoint],w*.0007,color,hudcol,cam)
    rod('地图定位点 '+fid,(target.x,target.y,-21.5),(target.x,target.y,-20.5),w*.0034,color,hudcol,cam,n=16)


maplabel('AGRI_014','A｜种薯 · 菌房 · 独立科研','近端0—3km规划分档',.16,-.035,colors[0],.29)
maplabel('AGRI_016','B｜番茄连栋 · 草莓高架','中段3—7km规划分档',.13,.16,colors[1],.30)
maplabel('AGRI_018','C｜水培育苗 · 秋烘车间','7—11km · 后续候选接入',-.045,.29,colors[2],.30)
maplabel('HUB_011','能源源区｜隔离板换＋CO₂热泵','PTES池式储热 · CO₂只在站内',.16,-.25,accent,.30)
maplabel('CITY_INTERFACE_V2','城市拟接口｜待核','新候选位置 · 非原电厂接入',-.47,.28,ink,.28)

viewdefs=[
 ('02 | 热泵枢纽','CAM_02 热泵站内三回路','热泵枢纽｜站内三回路剖面','蒸发器 → 压缩机 → 气冷器 → 节流阀 → 蒸发器','青：源侧水  |  紫：CO₂闭环  |  红/蓝：用户供回水  |  金：电输入'),
 ('02B | 源区与A区','CAM_02B 源区与A区','源区与A区｜同一地理位置','从热泵站定位到PTES、近端农业和独立科研示范','橙/蓝：一期隔离直供  |  红/蓝：二期候选干线  |  源区数据楼为体量代理'),
 ('03 | A区总览','CAM_03 A区种薯菌房科研','A区｜近端设施与独立科研','种薯组培＋原原种温室 · 工厂化食用菌 · 独立CO₂冷热与土壤储热','不同用途分别建模；5—10MW科研示范单列，不并入商业直供容量'),
 ('03A | 种薯温室','CAM_03A 种薯温室','A区｜种薯组培与原原种温室','洁净组培楼 · 苗床与育苗盘 · 独立换热接口','规划温室5万m² · 画面为代表性部分模型；屋面局部剖开展示'),
 ('03B | 食用菌','CAM_03B 食用菌厂房','A区｜工厂化食用菌','保温厂房 · 多层菌架与菌袋 · 空气处理与温控支路','规划2万m² · 菌房采用封闭保温建筑，前侧及部分屋面剖开展示'),
 ('03C | 独立科研','CAM_03C 土壤储热科研','A区｜CO₂冷热与土壤储热科研','独立机房 · 地下换热U管 · 监测点','5—10MW研究范围 · 土壤剖面为抬升解释窗口，深度非实测参数'),
 ('04 | 番茄温室','CAM_04 番茄温室','B区｜冬季番茄连栋温室','高跨屋架 · 吊蔓番茄行 · 栽培槽与分拣集配','规划20万m² · 画面为代表性部分模型；供回水支线经本区换热站'),
 ('04B | 草莓温室','CAM_04B 草莓温室','B区｜冬春草莓高架栽培','较低温室 · 高架栽培槽 · 采摘通道','规划5万m² · 与番茄分别建模和标识用户，接入属于二期候选'),
 ('05 | 水培育苗','CAM_05 水培育苗','C区｜叶菜水培与冷凉蔬菜种苗','水培槽 · 叶菜苗盘 · 种苗包装棚','规划1→8万m² · 后续接入候选，支线用虚线表示，不显示一期已供'),
 ('05B | 秋烘车间','CAM_05B 秋烘车间','C区｜燕麦与蔬菜秋烘中心','原粮料仓 · 输送廊道 · 烘干车间 · 热风换热器','9—10月低温秋烘 · 50—55℃热风需另行提温；紫色模块为提温示意'),
 ('02C | PTES储热','CAM_02C 池式储热','储热｜PTES池式热库','围堤 · 覆膜 · 储热水 · 独立充放热接口','规划体积50万m³ · 半盖剖面及外形为示意，不据此宣称保供时长')]
for name,camera_name,title,subtitle,foot in viewdefs:
    s=bpy.data.scenes.new(name); s.collection.children.link(root); s.camera=bpy.data.objects[camera_name]
    settings(s)
    bpy.context.window.scene=s
    bpy.context.view_layer.update()
    exclude(bpy.context.view_layer.layer_collection,display.name)
    hud(s,title,subtitle,foot)

# Keep the actual Google screenshot intact in an explicit reference view.
ref=bpy.data.scenes.new('00 | Google卫星对照')
rc=bpy.data.collections.new('Google原图对照 | 不作为地形纹理'); ref.collection.children.link(rc)
image=bpy.data.images.load(ROOT+'/research/map-v2/google-satellite-tilted.jpg'); image.pack()
m=flatmat('Google screenshot reference',(.8,.8,.8))
n=m.node_tree.nodes; e=next(i for i in n if i.type=='EMISSION'); t=n.new('ShaderNodeTexImage'); t.image=image
m.node_tree.links.new(t.outputs['Color'],e.inputs['Color'])
plate=mesh('Google原图 | 归属完整保留',[(-8,-4.51099,0),(8,-4.51099,0),(8,4.51099,0),(-8,4.51099,0)],[(0,1,2,3)],m,rc)
uv=plate.data.uv_layers.new(name='Original screenshot')
uv.data.foreach_set('uv',[0,0,1,0,1,1,0,1])
d=bpy.data.cameras.new('Google参考相机'); o=bpy.data.objects.new('Google参考相机',d); rc.objects.link(o); o.location=(0,0,20); d.type='ORTHO'; d.ortho_scale=18; d.clip_start=.1
ref.camera=o; settings(ref)
text('Google说明','Google Maps 实际截图对照｜保留原图归属',(-8,4.9,1),.31,ink,rc)
text('Google边界','此页为地图参考；可编辑地形采用独立DEM与Sentinel影像，不含Google城市网格。',(-8,-5.0,1),.18,ink,rc)
ref['reference_only']=True
bpy.ops.file.pack_all()
bpy.context.window.scene=overview
overview.camera=cam
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'/outputs/map-v2/乌兰察布_真实地理场景_v2.blend')
print({'stage':'presentation','geographic_views':len(viewdefs)+1,'google_reference_view':True,'objects':len(overview.objects),'file':bpy.data.filepath})
