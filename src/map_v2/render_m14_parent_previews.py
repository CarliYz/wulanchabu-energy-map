"""Render updated agricultural parent previews from the integrated M14 model."""
import bpy,json
from mathutils import Vector
BASE='/path/to/wulanchabu-energy-map'
assert bpy.data.filepath.endswith('/m14-sensors-integrated-v1/乌兰察布_测点整合场景_v1.blend')
review=bpy.data.scenes['M14 | 整合验收渲染']
camera=review.camera
original=(camera.location.copy(),camera.rotation_euler.copy(),camera.data.ortho_scale)
hidden={o.name:o.hide_render for o in review.objects}
receipts=[]
try:
    review.render.resolution_x=960
    review.render.resolution_y=640
    for oid in ['AGRI_014','AGRI_015','AGRI_016','AGRI_017']:
        root=bpy.data.objects[oid]
        members={root,*root.children_recursive}
        for o in review.objects:
            if o.type in {'MESH','CURVE','FONT'}:
                o.hide_render=hidden[o.name] or o not in members
        bpy.context.view_layer.update()
        points=[o.matrix_world@Vector(p) for o in members if o.type=='MESH' and not o.hide_render for p in o.bound_box]
        low=Vector(tuple(min(p[i] for p in points) for i in range(3)))
        high=Vector(tuple(max(p[i] for p in points) for i in range(3)))
        target=(low+high)/2
        scale=max((high-low).length*1.15,80)
        camera.location=target+Vector((scale*.35,-scale*.65,scale*.75))
        camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
        camera.data.ortho_scale=scale
        review.render.filepath=BASE+'/web/map-viewer/assets/integrated-v3/'+oid+'.png'
        result=bpy.ops.render.render(write_still=True,scene=review.name)
        assert 'FINISHED' in result
        receipts.append({'id':oid,'path':review.render.filepath})
finally:
    for o in review.objects:o.hide_render=hidden[o.name]
    camera.location,camera.rotation_euler,camera.data.ortho_scale=original
    review.render.resolution_x=1440
    review.render.resolution_y=1000
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print(json.dumps({'previews':receipts,'saved':bpy.data.filepath},ensure_ascii=False))
