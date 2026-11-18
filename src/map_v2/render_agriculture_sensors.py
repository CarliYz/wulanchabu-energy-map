"""Render the four standalone sensor candidates without hiding field geometry."""
import bpy
import json
from mathutils import Vector
BASE='/path/to/wulanchabu-energy-map'
OUT=BASE+'/outputs/m14-agriculture-sensors-v1'
assert bpy.data.filepath==OUT+'/乌兰察布_农业测点补模_v1.blend'
assert bpy.data.scenes.get('M14 | 农业测点验收渲染') is None
source=bpy.data.scenes['06 | 全区整合交互']
review=bpy.data.scenes.new('M14 | 农业测点验收渲染')
review.render.engine=source.render.engine
review.render.resolution_x=900
review.render.resolution_y=600
review.render.resolution_percentage=100
review.render.image_settings.file_format=next(i.identifier for i in bpy.types.ImageFormatSettings.bl_rna.properties['file_format'].enum_items if i.identifier=='PNG')
world=bpy.data.worlds.new('M14 | 白色展示环境')
world.use_nodes=True
background=next(n for n in world.node_tree.nodes if n.type=='BACKGROUND')
background.inputs['Color'].default_value=(.85,.85,.85,1)
background.inputs['Strength'].default_value=.6
review.world=world
collection=bpy.data.collections['M14 | 农业测点实体示意']
for obj in collection.objects:
    review.collection.objects.link(obj)
camera=bpy.data.objects.new('M14 | 仪表预览相机',bpy.data.cameras.new('M14 | 仪表预览相机'))
review.collection.objects.link(camera)
camera.data.type=next(i.identifier for i in bpy.types.Camera.bl_rna.properties['type'].enum_items if i.identifier=='ORTHO')
camera.data.ortho_scale=7.8
camera.data.clip_end=50000
review.camera=camera
light_type=next(i.identifier for i in bpy.types.Light.bl_rna.properties['type'].enum_items if i.identifier=='AREA')
light=bpy.data.objects.new('M14 | 仪表柔光',bpy.data.lights.new('M14 | 仪表柔光',type=light_type))
review.collection.objects.link(light)
light.data.energy=1100
light.data.size=6
floor_mat=bpy.data.materials.new('M14 | 展示地板')
floor_mat.use_nodes=True
bsdf=next(n for n in floor_mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
bsdf.inputs['Base Color'].default_value=(.82,.85,.87,1)
bsdf.inputs['Roughness'].default_value=.8
receipts=[]
for oid in ['AGRI_014_SENSOR','AGRI_015_SENSOR','AGRI_016_SENSOR','AGRI_017_SENSOR']:
    owner=bpy.data.objects[oid]
    if owner.name not in review.objects:
        review.collection.objects.link(owner)
    parent=owner.parent
    if parent.name not in review.objects:
        review.collection.objects.link(parent)
    floor_data=bpy.data.meshes.new('M14 | '+oid+' | 展示地板')
    floor_data.from_pydata([(-12,-12,-2.01),(12,-12,-2.01),(12,12,-2.01),(-12,12,-2.01)],[],[(0,1,2,3)])
    floor_data.materials.append(floor_mat)
    floor=bpy.data.objects.new(floor_data.name,floor_data)
    review.collection.objects.link(floor)
    # Keep presentation stages outside semantic facility hierarchies so a
    # later integrated export cannot collect them as sensor geometry.
    floor.matrix_world=owner.matrix_world.copy()
    target=owner.matrix_world.translation+Vector((0,0,-.1))
    camera.location=target+Vector((5,-8,4.4))
    camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
    light.location=target+Vector((1,-3,6))
    light.rotation_euler=(target-light.location).to_track_quat('-Z','Y').to_euler()
    review.render.filepath=OUT+'/'+oid+'.png'
    result=bpy.ops.render.render(write_still=True,scene=review.name)
    assert 'FINISHED' in result
    receipts.append({'object_id':oid,'path':review.render.filepath,'resolution':[900,600]})
bpy.context.window.scene=source
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print(json.dumps({'status':'rendered_standalone','previews':receipts,'saved':bpy.data.filepath,'active_scene':bpy.context.scene.name},ensure_ascii=False))
