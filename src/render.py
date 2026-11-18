"""Render the saved desktop scene with local Blender, without rebuilding business data."""
import bpy
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
scene=bpy.data.scenes['ENERGY_MVP']
if bpy.context.window:bpy.context.window.scene=scene
payload=json.loads((ROOT/'data/generated/results.json').read_text())
assert scene['input_sha256']==payload['input_sha256'],'saved scene/input mismatch'
scene.render.engine='BLENDER_EEVEE'
scene.render.image_settings.file_format='PNG'
scene.render.resolution_percentage=100
scene.render.use_file_extension=True
started=time.time()
if '--animation' in sys.argv:
    scene.render.resolution_x=1280;scene.render.resolution_y=720
    scene.eevee.taa_render_samples=16
    if '--ending-only' in sys.argv:
        scene.frame_start=397
    frames=ROOT/'outputs/frames';frames.mkdir(exist_ok=True,parents=True)
    scene.render.filepath=str(frames/'frame_')
    bpy.ops.render.render(animation=True,scene=scene.name)
    name='ending-render' if '--ending-only' in sys.argv else 'animation-render'
else:
    scene.render.resolution_x=1920;scene.render.resolution_y=1080
    scene.eevee.taa_render_samples=64
    for frame,name in [(170,'normal_t06'),(220,'buffer_t04'),(290,'outage_t06')]:
        scene.frame_set(frame);scene.render.filepath=str(ROOT/'outputs'/(name+'.png'))
        bpy.ops.render.render(write_still=True,scene=scene.name)
    name='stills-render'
(ROOT/'qc'/(name+'.json')).write_text(json.dumps({'operation':name,'outcome':'pass','seconds':time.time()-started,
    'input_sha256':scene['input_sha256'],'blender_version':bpy.app.version_string,
    'resolution':[scene.render.resolution_x,scene.render.resolution_y],'fps':scene.render.fps,
    'frame_range':[scene.frame_start,scene.frame_end]},indent=2))
print('RENDER_COMPLETE',name,time.time()-started)
