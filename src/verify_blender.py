"""Run with Blender --background --python; writes evaluated scene acceptance evidence."""
import bpy
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from build_scene import build
from scene_checks import verify_scene, signature

payload=json.loads((ROOT/'data/generated/results.json').read_text())
scene=bpy.data.scenes['ENERGY_MVP']
first=verify_scene(payload)
before=signature(scene)
scene=build(payload)
second=verify_scene(payload)
after=signature(scene)
assert before==after,'same-input rebuild changed IDs or transforms'
variant=json.loads((ROOT/'work/variant-results/results.json').read_text())
scene=build(variant)
changed=verify_scene(variant)
scene.frame_set(290)
assert (scene['delivered_mw'],scene['unserved_mw'])==(1,1)
scene=build(payload)
restored=verify_scene(payload)
scene.frame_set(170)
bpy.ops.file.pack_all()
report=dict(reopen=first,idempotent_rebuild=second,changed_input=changed,restored=restored,
            script_sha256=hashlib.sha256((ROOT/'src/build_scene.py').read_bytes()).hexdigest(),
            signature_sha256=hashlib.sha256(repr(after).encode()).hexdigest(),
            blender_version=bpy.app.version_string,review_mode='single_agent')
(ROOT/'qc/scene-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print('SCENE_ACCEPTANCE_PASS',json.dumps({'objects':len(after),'frames_checked_per_build':11,'variant_t6':[1,1]}))
