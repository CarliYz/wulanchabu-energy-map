"""Verify the distributed snapshot, runtime bindings and forbidden publication files."""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def main():
    manifest = json.loads((ROOT/'public-release-manifest.json').read_text())
    for name, digest in manifest['files'].items():
        path = (ROOT/name).resolve()
        assert path.is_relative_to(ROOT), name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, name
        assert path.stat().st_size < 100 * 1024**2, name
    for p in ROOT.rglob('*'):
        if '.git' in p.parts or not p.is_file() or 'node_modules' in p.parts or any(s.startswith('.venv') for s in p.parts):
            continue
        rel = p.relative_to(ROOT)
        assert rel.parts[0] not in {'inputs', 'research'}, rel
        assert p.suffix not in {'.blend', '.log'}, rel
        assert not p.name.startswith('.env'), rel
        # Report only the file path, never credential contents.
        assert not re.search(rb'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|AIza[A-Za-z0-9_-]{30,}|AKIA[A-Z0-9]{16})', p.read_bytes()), rel
        assert not re.search(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----', p.read_bytes()), rel
    asset = json.loads((ROOT/'web/map-prototype/integrated-asset.json').read_text())
    model = ROOT/'web/map-prototype'/asset['asset_url']
    assert hashlib.sha256(model.read_bytes()).hexdigest() == asset['sha256']
    assert len(asset['entity_nodes']) == 85
    fixtures = json.loads((ROOT/'data/contracts/fixtures/objects.json').read_text())
    for source in fixtures['sources'].values():
        assert hashlib.sha256((ROOT/source['path']).read_bytes()).hexdigest() == source['sha256'], source['path']
    print(json.dumps({'status':'pass','manifest_files':len(manifest['files']),'entities':85,'version':manifest['version']}))


if __name__ == '__main__':
    main()
