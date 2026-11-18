"""GEO + helpers.py are prepended. All assets are geographic scheme models."""
energy=col('03 能源设备 | 拟建')
agri=col('04 农业设施 | 代表模型')
turquoise=mat('源侧水 | 青',(.04,.6,.64),.3,.35)

# A: tissue culture and potato nursery, with a separate laboratory.
c=col('A1 | 种薯组培与温室',agri)
p=site('AGRI_014','种薯组培＋原原种温室',240,195,c)
greenhouse(p,c,-60,20,5,120,'potato')
greenhouse(p,c,10,20,5,120,'potato')
box('组培楼',(70,25,7),(55,70,14),white,c,p,1)
box('组培楼屋面',(70,25,14.5),(58,73,1),roofmat,c,p)
for y in (-2,16,34,52):
    box('实验室窗带',(41.9,y,8),(1,12,3),turquoise,c,p)
text('A1 用途','种薯组培 / 原原种温室',(-105,-87,1.2),6,dark,c,p)
text('A1 规模','代表模型 · 规划5万m²',(-105,-78,1.2),3.8,dark,c,p)
p['planned_area_m2']=50000; p['modeled_area_status']='representative_partial_not_full_planned_area'

# A: insulated mushroom factory. An open front bay exposes bags on shelves.
c=col('A2 | 封闭保温菌房',agri)
p=site('AGRI_015','工厂化食用菌',180,115,c)
for cx in (-42,42):
    box('菌房后墙',(cx,27,6),(72,1.1,12),white,c,p)
    for x in (cx-36,cx+36): box('菌房侧墙',(x,2,6),(1,51,12),white,c,p)
    box('菌房半剖屋面',(cx,14,12.5),(74,28,1),roofmat,c,p)
    for y in (-17,-5,7,19):
        for level in (1.8,4.2,6.6):
            box('菌架',(cx,y,level),(60,2.5,.22),steel,c,p)
            for x in range(int(cx-25),int(cx+26),6):
                rod('菌袋',(x,y,level+.2),(x,y,level+1.3),.7,white,c,p,n=8)
    box('菌房空气处理机',(cx,37,3),(20,9,6),steel,c,p, .4)
    pipe('菌房热水支管',[(cx,42,2),(cx+20,42,2),(cx+20,-25,2)],.35,red,c,p)
text('A2 用途','工厂化食用菌 / 保温菌房',(-80,-50,1),5.5,dark,c,p)
p['planned_area_m2']=20000

# B: taller tomato spans and hanging crop rows.
c=col('B1 | 番茄连栋温室',agri)
p=site('AGRI_016','冬季番茄连栋温室',250,220,c)
for x in (-70,0): greenhouse(p,c,x,20,6,155,'tomato')
box('番茄分拣与集配',(87,20,5),(46,100,10),white,c,p,.7)
text('B1 用途','冬季番茄 / 吊蔓连栋温室',(-112,-97,1),6.8,dark,c,p)
text('B1 规模','代表模型 · 规划20万m²',(-112,-86,1),4.5,dark,c,p)
p['planned_area_m2']=200000

# B: low strawberry benches, not tomato vines.
c=col('B2 | 草莓高架温室',agri)
p=site('AGRI_017','冬春草莓高架栽培',190,155,c)
for x in (-42,30): greenhouse(p,c,x,8,5,105,'strawberry')
text('B2 用途','冬春草莓 / 高架栽培',(-83,-68,1),6,dark,c,p)
p['planned_area_m2']=50000

# C: hydroponics and separate seedling packing facility.
c=col('C1 | 叶菜水培与种苗',agri)
p=site('AGRI_018','叶菜水培＋冷凉蔬菜种苗',190,150,c)
for x in (-47,20): greenhouse(p,c,x,10,5,100,'leaf')
box('种苗包装棚',(72,7,4),(28,65,8),white,c,p,.5)
text('C1 用途','叶菜水培 / 冷凉蔬菜种苗',(-86,-66,1),5.4,dark,c,p)
p['planned_area_m2_range']=[10000,80000]; p['connection_status']='future_candidate_not_P1_connected'

# C: recognizable grain/vegetable dryer, silos, conveyor and heat exchanger.
c=col('C2 | 秋烘车间',agri)
p=site('DRY_019','燕麦及脱水蔬菜秋烘',190,155,c)
box('烘干车间',(25,15,9),(85,65,18),white,c,p,.6)
roof('烘干车间屋顶',25,15,88,68,18,24,roofmat,c,p)
for x in (-65,-36):
    rod('原粮料仓',(x,35,0),(x,35,27),11,steel,c,p,n=20)
    roof('料仓锥顶',x,35,23,23,27,34,steel,c,p)
    box('料仓出料口',(x,35,1),(9,9,2),gold,c,p)
    pipe('输送廊道',[(x,22,8),(x,-10,8),(25,-10,8)],1.2,steel,c,p)
for x in (2,24,46):
    box('热风换热器',(x,-37,4),(15,11,8),steel,c,p,.4)
    for y in (-41,-38,-35,-32): box('换热器翅片',(x,y,4),(16,.3,7),roofmat,c,p)
    pipe('秋烘热水',[(x,-45,1),(x,-42,1),(x,-42,4)],.35,red,c,p)
box('秋烘提温模块',(75,-35,4),(19,15,8),purple,c,p,.4)
text('C2 用途','9—10月秋烘 / 燕麦与蔬菜',(-83,-65,1),5.5,dark,c,p)
p['connection_status']='future_candidate'; p['temperature_note']='50—55℃热风需另行提温，非45℃直接生成'

# A independent research module, with a lifted sectional soil window.
c=col('A3 | 独立CO2冷热与土壤储热',energy)
p=site('DEMO_013','独立5—10MW科研示范',155,135,c)
box('科研机房',(-42,12,5),(45,55,10),white,c,p,.7)
roof('科研机房屋顶',-42,12,48,58,10,14,roofmat,c,p)
box('土壤储热剖面窗口',(26,25,7),(65,34,14),soil,c,p)
box('土壤剖面底层',(26,-5,1),(65,26,2),soil,c,p)
for x in (-4.5,56.5): box('土壤剖面侧壁',(x,-5,7),(4,26,14),soil,c,p)
for x in (5,19,33,47):
    pipe('地下换热U管示意',[(x,-16,17),(x,-16,2),(x+6,-16,2),(x+6,-16,17)],.48,purple,c,p)
    rod('监测立柱',(x,-23,0),(x,-23,8),.35,gold,c,p)
pipe('科研冷热支路',[(-18,-10,2),(10,-10,2),(10,-20,17)],.5,blue,c,p)
text('A3 用途','独立科研 / CO₂冷热＋土壤储热',(-68,-58,1),4.8,dark,c,p)
text('A3 剖面','土壤剖面抬升示意 · 非实际埋深',(-68,-48,1),3.4,dark,c,p)
p['research_capacity_MW_range']=[5,10]; p['cutaway_display_only']=True

# Main energy hub: cutaway shed, isolation HX and two representative CO2 trains.
c=col('HUB_011 | 板换＋CO2热泵站',energy)
p=site('HUB_011','源侧隔离板换与CO2跨临界热泵',210,150,c)
box('热泵站后墙',(-7,47,11),(150,1.2,22),white,c,p)
for x in (-81,67):
    for y in (-45,0,45): rod('机房钢柱',(x,y,0),(x,y,22),.7,steel,c,p)
box('机房局部屋面',(-7,34,22.5),(154,30,1),roofmat,c,p)
box('控制室',(-64,-38,6),(27,22,12),white,c,p,.5)
box('隔离板换',(83,-31,7),(10,17,14),steel,c,p,.3)
for i in range(8): box('板换换热片',(78+i*1.3,-31,7),(.3,18,14.5),turquoise,c,p)
for yy in (-8,20):
    box('蒸发器',(-42,yy,6),(20,10,12),turquoise,c,p,.5)
    for x in (-49,-45,-41,-37,-33): rod('蒸发换热筒',(x,yy-6,6),(x,yy+6,6),1,steel,c,p)
    rod('CO2压缩机',(-10,yy,2),(-10,yy,12),4.7,purple,c,p,n=20)
    rod('压缩机电动机',(-10,yy-8,5),(-10,yy-3,5),3,steel,c,p,n=16)
    rod('气冷器',(12,yy,7),(43,yy,7),4,steel,c,p,n=20)
    for x in (16,24,32,40): rod('气冷器支撑',(x,yy,0),(x,yy,4),.8,roofmat,c,p)
    box('节流阀',(0,yy-9,2),(4,4,4),purple,c,p,.4)
    # Closed refrigerant path with explicit components in order.
    loop=[(-42,yy,13),(-10,yy,13),(-10,yy,15),(24,yy,15),(24,yy-9,15),(24,yy-9,2),(0,yy-9,2),(-42,yy-9,2),(-42,yy,2),(-42,yy,13)]
    o=pipe('CO2闭环 | 蒸发→压缩→气冷→节流',loop,.6,purple,c,p)
    o['circuit']='CO2_station_internal_closed'
    pipe('源侧水 | 蒸发器入口',[(-55,yy,5),(-55,yy-5,5),(-42,yy-5,5)],.5,turquoise,c,p)
    pipe('用户供水 | 气冷器出口',[(43,yy,7),(58,yy,7),(58,yy,2)],.55,red,c,p)
pipe('P1隔离直供接口',[(83,-22,4),(93,-22,4),(93,58,4)],.65,red,c,p)
pipe('P1隔离回水接口',[(83,-40,3),(99,-40,3),(99,58,3)],.65,blue,c,p)
pipe('P2供水总管',[(58,-8,2),(58,60,2),(45,60,2)],.75,red,c,p)
pipe('P2回水总管',[(64,-8,2),(64,64,2),(45,64,2)],.75,blue,c,p)
pipe('源水外接口',[(80,-31,4),(100,-31,4),(100,-61,4)],.7,turquoise,c,p)
pipe('源回水外接口',[(80,-35,3),(104,-35,3),(104,-61,3)],.7,blue,c,p)
pipe('压缩机独立电输入',[(-10,-72,2),(-10,-25,2),(-10,-16,5)],.4,gold,c,p)
text('HUB 用途','CO₂热泵枢纽 / 源水·制冷剂·用户水分回路',(-92,-67,1),4.2,dark,c,p)
text('HUB 温级','源水约45℃ → 近端隔离直供；二期用户水目标85℃',(-92,-59,1),3.5,dark,c,p)
p['representative_equipment_not_manufacturer_spec']=True
p['port_P2_supply_local']=[45,60,2]; p['port_P2_return_local']=[45,64,2]
p['port_P1_supply_local']=[93,58,4]; p['port_P1_return_local']=[99,58,3]
p['port_source_in_local']=[100,-61,4]; p['port_source_out_local']=[104,-61,3]

# PTES is a pit, not the old test tank. The half lid reveals the reservoir.
c=col('STORE_012 | PTES池式储热',energy)
p=site('STORE_012','PTES日周调节池式储热',320,240,c)
liner=mat('PTES | 深色覆膜',(.055,.08,.085),.12,.55)
water=mat('PTES | 储热水',(.045,.29,.38),.25,.22)
box('池体围堤',(0,0,3),(295,215,6),soil,c,p)
box('池内覆膜',(0,0,6.2),(270,190,.6),liner,c,p)
box('储热水剖面',(0,-20,6.7),(253,138,.5),water,c,p)
box('浮盖剖开展示',(0,51,9),(275,87,1.5),white,c,p)
for x in range(-125,126,15): box('覆膜压条',(x,51,9.9),(.7,87,.3),steel,c,p)
for x in (-134,134): box('边缘维护步道',(x,0,7.8),(6,203,.8),slab,c,p)
pipe('PTES充放接口',[(138,-61,3),(115,-61,3),(115,-61,8),(35,-61,8)],.85,red,c,p)
pipe('PTES回路接口',[(138,-68,2),(105,-68,2),(105,-68,7),(35,-68,7)],.85,blue,c,p)
text('PTES 用途','PTES 池式储热 / 半盖剖面',(-139,-110,1),6,dark,c,p)
text('PTES 规模','规划体积50万m³ · 外形为方案示意',(-139,-99,1),4,dark,c,p)
p['planned_volume_m3']=500000; p['geometry_not_sized_from_capacity']=True
p['port_supply_local']=[138,-61,3]; p['port_return_local']=[138,-68,2]

# Existing-context data centres are footprint proxies at unverified historical points.
for fid in ('DC_004','DC_005','DC_006'):
    c=col(fid+' | 数据中心体量代理',energy)
    p=site(fid,'数据中心余热候选接口体量代理',235,175,c)
    for x in (-65,35):
        box('数据楼体量',(x,10,10),(70,110,20),white,c,p,1)
        for y in (-27,0,27):
            box('屋顶冷却设备',(x,y,23),(46,17,6),roofmat,c,p,.6)
            for xx in (x-12,x+12): rod('冷却风机',(xx,y,26),(xx,y,27),5,steel,c,p,n=12)
    box('隔离换热接口',(99,-56,4),(14,18,8),turquoise,c,p,.4)
    p['footprint_status']='proxy_not_existing_building_survey'
    text(fid+'用途','数据中心体量代理 / 余热接口待核',(-107,-79,1),4.7,dark,c,p)

# Preserve site camera bookmarks in the same geographic coordinate system.
cams=col('07 地理相机')
def bookmark(name,target,scale,dx=0,dy=-700,dz=850):
    d=bpy.data.cameras.new(name); o=bpy.data.objects.new(name,d); cams.objects.link(o)
    o.location=Vector(target)+Vector((dx,dy,dz)); o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
    d.type='ORTHO'; d.ortho_scale=scale; d.clip_end=100000; d.clip_start=.1
    return o
hub=bpy.data.objects['HUB_011']
bookmark('CAM_02 热泵站内三回路',tuple(hub.location+Vector((0,0,7))),290,dx=110,dy=-240,dz=245)
bookmark('CAM_02B 源区与A区',(-40,430,130),2250,dy=-2200,dz=2600)
potato=bpy.data.objects['AGRI_014']; mushroom=bpy.data.objects['AGRI_015']; demo=bpy.data.objects['DEMO_013']
center=(potato.location+mushroom.location+demo.location)/3
bookmark('CAM_03 A区种薯菌房科研',tuple(center),2100,dy=-1700,dz=2200)
for name,fid,scale in [('CAM_03A 种薯温室','AGRI_014',380),('CAM_03B 食用菌厂房','AGRI_015',290),('CAM_03C 土壤储热科研','DEMO_013',240),('CAM_04 番茄温室','AGRI_016',390),('CAM_04B 草莓温室','AGRI_017',310),('CAM_05 水培育苗','AGRI_018',300),('CAM_05B 秋烘车间','DRY_019',310),('CAM_02C 池式储热','STORE_012',490)]:
    p=bpy.data.objects[fid]
    bookmark(name,tuple(p.location+Vector((0,0,5))),scale,dx=scale*.18,dy=-scale*.85,dz=scale*.85)
bpy.context.view_layer.update()
scene.camera=bpy.data.objects['CAM_02 热泵站内三回路']
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'/checkpoints/map-v2/02-facilities.blend')
print({'stage':'M3','objects':len(scene.objects),'assets':[o.name for o in scene.objects if 'asset_id' in o],'saved':'02-facilities.blend'})
