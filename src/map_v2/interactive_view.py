"""Enable Blender's native pan hand and cursor-centered zoom in the live UI."""
import bpy
from mathutils import Vector

name = '00 | 交互地图·小手平移'
interactive = bpy.data.scenes.get(name)
overview = bpy.data.scenes['01 | 地理总览']
if interactive is None:
    interactive = bpy.data.scenes.new(name)
    interactive.collection.children.link(bpy.data.collections['MAP_V2'])
interactive.world = overview.world
interactive.render.engine = overview.render.engine
interactive.camera = overview.camera
interactive['navigation'] = '右上角小手拖动平移；鼠标放目标处，向上滚轮深入；中键拖动旋转'
interactive['requirement_revision'] = 'map-design-v2+native-navigation'
interactive['imagery_source'] = 'EOxCloudless / EOX, Copernicus Sentinel-2 2024; CC BY-NC-SA 4.0'
bpy.context.window.scene = interactive
bpy.context.view_layer.update()

def exclude_navigation_helpers(layer):
    if layer.name in ('07 地理相机', '08 总览标签', '09 总览管线强调 | 非真实管径'):
        layer.exclude = True
    for child in layer.children:
        exclude_navigation_helpers(child)

exclude_navigation_helpers(bpy.context.view_layer.layer_collection)
bpy.context.preferences.inputs.use_zoom_to_mouse = True
bpy.context.preferences.inputs.use_mouse_depth_navigate = True
for area in bpy.context.screen.areas:
    if area.type != 'VIEW_3D':
        continue
    space = area.spaces.active
    space.show_gizmo = True
    space.show_gizmo_navigate = True
    space.show_region_ui = False
    space.clip_start = .1
    space.clip_end = 100000
    space.overlay.show_floor = False
    space.overlay.show_axis_x = False
    space.overlay.show_axis_y = False
    space.shading.type = 'MATERIAL'
    region = space.region_3d
    region.view_perspective = 'PERSP'
    region.view_rotation = overview.camera.rotation_euler.to_quaternion()
    region.view_location = Vector((-2000, 2700, 130))
    region.view_distance = 19000
    area.tag_redraw()

print({'scene': interactive.name, 'zoom_to_mouse': bpy.context.preferences.inputs.use_zoom_to_mouse,
       'mouse_depth': bpy.context.preferences.inputs.use_mouse_depth_navigate,
       'views': [{'perspective': a.spaces.active.region_3d.view_perspective,
                  'hand': a.spaces.active.show_gizmo_navigate}
                 for a in bpy.context.screen.areas if a.type == 'VIEW_3D']})
