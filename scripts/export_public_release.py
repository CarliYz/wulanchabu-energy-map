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
PREFIXES = ('.github/', 'web/', 'src/', 'scripts/', 'tests/', 'data/', 'qa/', 'design/m7/map-assets/',
            'qc/m14-sensors-integrated-v1/geography/')
DOCS = ['docs/ARCHITECTURE.md', 'docs/PUBLIC_RELEASE.md', 'docs/QA_CURRENT.md', 'docs/SINGLE_FILE_HTML.md', 'docs/images/overview.png',
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
    version = json.loads((ROOT/'package.json').read_text())['version']
    source_head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    eligible = {f for f in tracked if f.startswith(PREFIXES) and not (
        f.endswith('.log') or '/evidence/' in f or '/node_modules/' in f)}
    eligible.update(TOP + DOCS)
    eligible.update(str(p.relative_to(ROOT)) for p in (ROOT/'scripts').glob('*public_release.py'))
    eligible.add('scripts/build_single_file_html.py')
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

当前隔离配置是 e2e.closeout.config.js，默认测试端口18867（ENERGY_QA_PORT可更改），自动启停自己的服务，拒绝复用其他工作区的服务；不会接管已有8767。

```sh
cd qa/agent-e2e
npm ci
npx playwright install chromium
E2E_TELEMETRY_DISABLED=1 npx e2e run --config e2e.closeout.config.js
```

完整 CLI 参数以锁定版本的 npx e2e --help 为准。九个既有文件与runtime-closeout.e2e.js共同覆盖当前场景。e2e.config.js / viewer.e2e.js 和根目录 Playwright 默认配置是历史 viewer，不能混算为当前新版验收。当前命令及证据语义见docs/QA_CURRENT.md。

Jev preflight：node jev-preflight.mjs。缺 TYPESAFE_AI_API_KEY 时明确退出2，不发起模型调用。凭据仅经进程环境提供，不写入仓库。全局 MCP 注册不随克隆自动完成；查看演示不需要 MCP。

历史 M14 的96种行为为分组通过证据；本次发布的文件身份以根目录 public-release-manifest.json 为准，当前运行边界见 RELEASE.md。
''')
    transforms.append({'path': 'qa/agent-e2e/README.md', 'change': 'public current-entry QA instructions'})
    (out/'.gitignore').write_text('''__pycache__/\n*.pyc\n.DS_Store\n.venv*/\nnode_modules/\noutputs/\nwork/\ncheckpoints/\ninputs/\nresearch/\n*.blend\n*.blend1\n*.log\n.env\n.env.*\n!.env.example\ntest-results/\nplaywright-report/\nqa/agent-e2e/.e2e*/\nqa/agent-e2e/artifacts/\n''')
    (out/'.gitattributes').write_text('*.csv -text whitespace=cr-at-eol\n')
    (out/'RELEASE.md').write_text(f'''# 乌兰察布能源三维地图 v{version}

这是可本地运行的候选方案演示包。它包含 HTML / Three.js / MapLibre 工作台、Blender 导出的 GLB、三种底图、设施详情、候选关系、分析空态和审计入口。

## 启动

在本目录执行：

```sh
python3 launch.py
```

也可以直接执行：

```sh
python3 web/map-prototype/serve.py
```

然后访问终端打印的本机地址。不要用 `file://` 直接双击 `index.html`，因为模型和 JSON 需要 HTTP 服务读取。单文件 HTML 另见 `docs/SINGLE_FILE_HTML.md`，并随 GitHub Release 提供。

入口文件：`web/map-prototype/index.html`。

## 运行条件

Python 3、支持 WebGL 的桌面浏览器，以及固定版本 Three.js / MapLibre CDN 网络。查看演示不需要 Blender、Node.js 或 MCP。

## 版本证据

- 源提交：`{source_head[:7]}`
- 本文件由导出器生成，不代表已经执行测试。
- 当前运行测试命令与范围：`docs/QA_CURRENT.md`。
- 实际 CI 结果：<https://github.com/CarliYz/wulanchabu-energy-map/actions>。
- 本版本发行回执与附件校验：<https://github.com/CarliYz/wulanchabu-energy-map/releases/tag/v{version}> 中的 `release-verification.json` 和 `SHA256SUMS.txt`。
- 可执行发布包校验：`python3 scripts/verify_public_release.py`。

## 当前边界

这是候选方案与数据关系演示。独立控制点、岸线/地籍、管网许可与水力、四测点真实 PLC 接管、真实时序、Google Maps API、Jev 在线视觉验证和生产迁移仍需后续输入与验收。
''')
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
    manifest = dict(version=version, source_head=source_head,
        source_branch='codex/energy-map-v2', files=files, source_sha256=originals,
        transforms=transforms, historical_m14_identity={'unchanged': unchanged, 'changed': changed, 'omitted': omitted},
        excluded=['original inputs/research/private logs', 'original git history', 'native blend', 'node_modules', 'unrelated dirty test evidence'])
    (out/'public-release-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'output':str(out),'files':len(files),'bytes':sum(p.stat().st_size for p in out.rglob('*') if p.is_file()),
        'transforms':len(transforms),'historical_unchanged':len(unchanged),'historical_changed':changed},ensure_ascii=False))


if __name__ == '__main__':
    main()
