"""Verify original package and all original member digests before dependent work."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

if __name__=='__main__':
    m=json.loads((ROOT/'inputs/manifest.json').read_text())
    assert digest(ROOT/'inputs/source-materials.zip')==m['archive_sha256'], 'source archive mismatch'
    for f in m['files']:
        p=ROOT/'inputs/original'/f['path']
        assert p.stat().st_size==f['bytes'] and digest(p)==f['sha256'], f['path']
    sources=json.loads((ROOT/'data/sources.json').read_text())
    for s in sources['items']:
        assert digest(ROOT/'research'/s['id'])==s['sha256'],s['id']
    print(json.dumps({'operation':'source-preflight','outcome':'pass','archive_sha256':m['archive_sha256'],
                      'original_members':len(m['files']),'public_sources':len(sources['items'])}))
