"""Check current UI source identities; --write refreshes them after review."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = {
    'web/map-prototype/app.mjs': '网页运行时',
    'web/map-prototype/index.html': '工作台入口',
    'web/map-prototype/style.css': '工作台布局',
    'web/map-prototype/workspace-layout.mjs': '浮动界面与相机取景边界',
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    path = ROOT / 'web/map-prototype/audit-manifest.json'
    audit = json.loads(path.read_text())
    entries = {item['path']: item for item in audit['source_inventory']}
    for name, label in RUNTIME.items():
        digest = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        if args.write:
            item = entries.get(name)
            if item is None:
                item = {'path': name, 'label': label, 'status': 'candidate', 'status_label': '源码身份；工程状态另列'}
                audit['source_inventory'].append(item)
            item.update(sha256=digest, version='m17-responsive-closeout-v1')
        else:
            if name not in entries or entries[name]['sha256'] != digest:
                raise SystemExit(f'Stale runtime audit identity: {name}; review then run --write')
    if args.write:
        audit['runtime_revision'] = 'm17-responsive-closeout-v1 · m14-sensors-integrated-v1'
        for item in audit['source_inventory']:
            if item['path'] == 'web/map-prototype/integrated-asset.json':
                item['status_label'] = '85对象·位置待独立配准'
        path.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'status': 'pass', 'operation': 'refresh' if args.write else 'check', 'runtime_sources': len(RUNTIME)}))


if __name__ == '__main__':
    main()
