"""Render isolated system groups plus their declared, connected schematic geometry."""
import bpy
import json
from mathutils import Vector

BASE='/path/to/wulanchabu-energy-map'
assert bpy.data.filepath.endswith('/m12-connected-v1/乌兰察布_连接整合场景_v1.blend')
original=bpy.context.window.scene
review=bpy.data.scenes['M12 | 连接验收渲染']
camera=review.camera
old_camera=(camera.location.copy(),camera.rotation_euler.copy(),camera.data.ortho_scale)
hidden={o.name:o.hide_render for o in review.objects}
groups={
    'DRY_019': ['M10_C2_SYSTEM','DRY_019'],
    'STORE_012':['M10_PTES_SYSTEM','STORE_012'],
    'HUB_011':['HUB_011_ROLE_MAPPING','HUB_011'],
    'BOILER_CAND_001':['BOILER_CAND_001'],
}
receipts=[]
try:
    bpy.context.window.scene=review
    review.cycles.samples=24
    review.render.resolution_x=960;review.render.resolution_y=640
    for facility_id,roots in groups.items():
        members=set()
        for root_name in roots:
            root=bpy.data.objects[root_name];members.add(root);members.update(root.children_recursive)
        # Device roots are intentionally independent semantic nodes.
        prefixes=['DRY_019'] if facility_id=='DRY_019' else ['STORE_012'] if facility_id=='STORE_012' else ['HUB_011','HUB_POWER'] if facility_id=='HUB_011' else ['BOILER_CAND_001','GREEN_POWER']
        for obj in review.objects:
            if obj.get('object_id') and any(obj.get('object_id','').startswith(p) for p in prefixes):members.add(obj)
        for obj in review.objects:
            if obj.type in {'MESH','CURVE','FONT'}:obj.hide_render=hidden[obj.name] or obj not in members
        bpy.context.view_layer.update()
        # Frame equipment, not the long candidate pipes to neighboring systems.
        points=[obj.matrix_world@Vector(p) for obj in members if obj.type=='MESH' and not obj.hide_render for p in obj.bound_box]
        low=Vector(tuple(min(p[i] for p in points) for i in range(3)));high=Vector(tuple(max(p[i] for p in points) for i in range(3)))
        target=(low+high)/2;scale=max((high-low).length*1.3,80)
        camera.location=target+Vector((scale*.35,-scale*.65,scale*.75))
        camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=scale
        review.render.filepath=BASE+'/web/map-viewer/assets/integrated-v2/'+facility_id+'.png'
        result=bpy.ops.render.render(write_still=True);assert 'FINISHED' in result
        receipts.append({'id':facility_id,'path':review.render.filepath,'resolution':[960,640]})
finally:
    for obj in review.objects:obj.hide_render=hidden[obj.name]
    camera.location,camera.rotation_euler,camera.data.ortho_scale=old_camera
    review.render.resolution_x=1440;review.render.resolution_y=1000
    bpy.context.window.scene=original
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print(json.dumps({'previews':receipts,'saved':bpy.data.filepath},ensure_ascii=False))
