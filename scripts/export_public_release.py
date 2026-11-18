# -*- coding: utf-8 -*-
"""Export the current code and runnable assets without private source materials/history."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
TOP = ['README.md', 'CHANGELOG.md', 'THIRD_PARTY_NOTICES.md', 'GLOSSARY.md',
       'package.json', 'package-lock.json', 'requirements-contracts.txt',
       'playwright.config.mjs', 'launch.py', '打开三维系统.command']
PREFIXES = ('web/', 'src/', 'scripts/', 'tests/', 'data/', 'qa/', 'design/m7/map-assets/',
            'qc/m14-sensors-integrated-v1/geography/')
DOCS = ['docs/ARCHITECTURE.md', 'docs/PUBLIC_RELEASE.md', 'docs/images/overview.png',
        'qc/c-zone-audit-before.json']
PERSONAL_PREFIX = '/path/to/wulanchabu-energy-map'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    out = Path(args.output).resolve()
    if out.exists():
        raise SystemExit('Output must not exist; preserve previous publication snapshots')
    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    eligible = {f for f in tracked if f.startswith(PREFIXES) and not (
        f.endswith('.log') or '/evidence/' in f or '/node_modules/' in f)}
    eligible.update(TOP + DOCS)
    eligible.update(str(p.relative_to(ROOT)) for p in (ROOT/'scripts').glob('*public_release.py'))
    eligible = {f for f in eligible if (ROOT/f).is_file()}
    out.mkdir(parents=True)
    transforms = []
    originals = {}
    for f in sorted(eligible):
        src, dest = ROOT/f, out/f
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        originals[f] = sha(src)
        if src.suffix in {'.py', '.mjs', '.js', '.json', '.md', '.toml'}:
            s = dest.read_text()
            if PERSONAL_PREFIX in s:
                dest.write_text(s.replace(PERSONAL_PREFIX, '/path/to/wulanchabu-energy-map'))
                transforms.append({'path': f, 'change': 'replace personal workspace prefix with configuration placeholder'})
    fixture = out/'data/contracts/fixtures/objects.json'
    objects = json.loads(fixture.read_text())
    objects['sources']['PLAN'].update(path='docs/ARCHITECTURE.md',
        locator='公开业务合同：C1热水/营养液隔离、CO2站内循环与候选状态', sha256=sha(out/'docs/ARCHITECTURE.md'))
    objects['sources']['AUDIT']['sha256'] = sha(out/objects['sources']['AUDIT']['path'])
    fixture.write_text(json.dumps(objects, ensure_ascii=False, indent=2)+'\n')
    transforms.append({'path': str(fixture.relative_to(out)), 'change': 'bind planning fixture to public architecture; refresh sanitized historical sample digest'})
    (out/'qa/agent-e2e/README.md').write_text('''# 当前工作台交互测试

当前配置是 e2e.map-prototype.config.js，固定入口 http://127.0.0.1:8767/web/map-prototype/，会按配置启动 / 复用该服务。源码与运行 URL 必须来自同一仓库。

```sh
cd qa/agent-e2e
npm ci
npx playwright install chromium
E2E_TELEMETRY_DISABLED=1 npx e2e run --config e2e.map-prototype.config.js
```

测试按文件分组执行以适应工具超时。完整 CLI 参数以锁定版本的 npx e2e --help 为准。map-prototype、c1-devices、energy-paths、analysis-audit、ab-terminals、m10-system-devices、integrated-model、geographic-review、agriculture-sensors 分别覆盖当前场景。e2e.config.js / viewer.e2e.js 和根目录 Playwright 默认配置是历史 viewer，不能混算为当前新版验收。

Jev preflight：node jev-preflight.mjs。缺 TYPESAFE_AI_API_KEY 时明确退出2，不发起模型调用。凭据仅经进程环境提供，不写入仓库。全局 MCP 注册不随克隆自动完成；查看演示不需要 MCP。

历史 M14 的96种行为为分组通过证据；本次发布是否复跑以根目录 qc/public-release-verification.json 为准。
''')
    transforms.append({'path': 'qa/agent-e2e/README.md', 'change': 'public current-entry QA instructions'})
    (out/'.gitignore').write_text('''__pycache__/\n*.pyc\n.DS_Store\n.venv*/\nnode_modules/\noutputs/\nwork/\ncheckpoints/\ninputs/\nresearch/\n*.blend\n*.blend1\n*.log\n.env\n.env.*\n!.env.example\ntest-results/\nplaywright-report/\nqa/agent-e2e/.e2e*/\nqa/agent-e2e/artifacts/\n''')
    files = {str(p.relative_to(out)): sha(p) for p in out.rglob('*') if p.is_file()}
    identity = json.loads((ROOT/'qc/m14-sensors-integrated-v1/tested-identity.json').read_text())
    unchanged, changed, omitted = [], [], []
    for name, digest in identity['hashes'].items():
        if name not in files:
            omitted.append(name)
        elif files[name] == digest:
            unchanged.append(name)
        else:
            changed.append(name)
    manifest = dict(version='0.3.0-rc.1', source_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source_branch='codex/energy-map-v2', files=files, source_sha256=originals,
        transforms=transforms, historical_m14_identity={'unchanged': unchanged, 'changed': changed, 'omitted': omitted},
        excluded=['original inputs/research/private logs', 'original git history', 'native blend', 'node_modules', 'unrelated dirty test evidence'])
    (out/'public-release-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'output':str(out),'files':len(files),'bytes':sum(p.stat().st_size for p in out.rglob('*') if p.is_file()),
        'transforms':len(transforms),'historical_unchanged':len(unchanged),'historical_changed':changed},ensure_ascii=False))


if __name__ == '__main__':
    main()
