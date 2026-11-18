"""Assemble a portable review package from the frozen working tree."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='outputs/能源地图_演示交付_20261117')
    parser.add_argument('--verification-dir',default='qc/m12-connected-v1')
    parser.add_argument('--geographic-dir',default='qc/m13-geographic-review-v1')
    parser.add_argument('--batch-doc',default='docs/batches/m13-geographic-ui-v1.md')
    args=parser.parse_args();out=ROOT/args.output
    verification=ROOT/args.verification_dir
    integrated=json.loads((ROOT/'web/map-prototype/integrated-asset.json').read_text())
    blend=integrated['blender_source']
    out.mkdir(parents=True,exist_ok=True)
    files=[]
    for directory in ['web/map-prototype','web/map-viewer/assets','design/m7/map-assets']:
        files.extend(p for p in (ROOT/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    files.extend(ROOT/p for p in ['data/map-v2/geographic-manifest.json','data/map-v2/routes.json',
        'data/contracts/coordinate-contract.json',blend,
        'docs/batches/m12-connected-v1.md','docs/DELIVERY_20261117.md','docs/NEXT_STEPS_20261117.md',
        'qc/m12-connected-v1/acceptance-summary.json','qc/m12-connected-v1/tested-identity.json',
        'qc/m12-connected-v1/package-browser-verification.json',
        'qc/m13-geographic-review-v1/geographic-review.md','qc/m13-geographic-review-v1/geographic-review.json',
        'qc/m13-geographic-review-v1/c1-public-water-review.svg','qc/m13-geographic-review-v1/c1-public-water-review.png',
        'qc/m13-geographic-review-v1/display-pads.json','qc/m13-geographic-review-v1/public-features.geojson',
        'qc/m11-integrated-v1/public-screening/public-source-receipt.json',
        *[f'qc/m11-integrated-v1/public-screening/public-{kind}-2026-11-17.json' for kind in ['highway','railway','waterway','waterbody']]])
    identity=json.loads((verification/'tested-identity.json').read_text())
    if verification != ROOT/'qc/m12-connected-v1':
        files.extend([verification/'acceptance-summary.json',verification/'tested-identity.json',ROOT/args.batch_doc])
        files.extend(p for p in (ROOT/args.geographic_dir).iterdir() if p.is_file())
        if (verification/'package-browser-verification.json').exists():
            files.append(verification/'package-browser-verification.json')
    for name,digest in identity['hashes'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest, f'Tested product changed: {name}'
    inventory={}
    for src in files:
        relative=src.relative_to(ROOT);target=out/relative;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(src,target)
        digest=hashlib.sha256(src.read_bytes()).hexdigest()
        assert hashlib.sha256(target.read_bytes()).hexdigest()==digest
        inventory[str(relative)]=digest
    launcher='''from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import webbrowser

root = Path(__file__).resolve().parent
server = ThreadingHTTPServer(("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=str(root)))
url = f"http://127.0.0.1:{server.server_port}/web/map-prototype/"
print("三维系统已启动：" + url, flush=True)
print("关闭本窗口或按 Ctrl+C 退出。地图与模型在本机，Three.js 和 MapLibre 组件需要联网加载。", flush=True)
webbrowser.open(url)
try:
    server.serve_forever()
except KeyboardInterrupt:
    pass
finally:
    server.server_close()
'''
    (out/'launch.py').write_text(launcher)
    command=out/'打开三维系统.command';command.write_text('#!/bin/zsh\npython3 "$(dirname "$0")/launch.py"\n');command.chmod(0o755)
    instructions='''# 能源地图三维演示交付

2026-11-17，M12 连接整合版。双击“打开三维系统.command”；需要 Python 3 和可加载 Three.js / MapLibre CDN 的网络。终端窗口内显示实际地址，Ctrl+C 退出。HTML 使用本地 HTTP 读取模型，不能直接用 file:// 双击 index.html。

默认标准地图。顶部切换卫星、标准地图、数据/DEM；左栏箭头展开索引，搜索设备并点击聚焦；右侧详情可查看模型图、属性和候选关系；点管段高亮，再点或按 Esc 清除。Esc 逐层退出，详情右上角 × 关闭。小手平移，滚轮缩放。

Blender 工程位于 outputs/m12-connected-v1/乌兰察布_连接整合场景_v1.blend，打开“06 | 全区整合交互”；另有“02 | 热泵枢纽”等细节场景。四张新系统渲染图在 web/map-viewer/assets/integrated-v2/，四农业图在 integrated-v1/。

85可选对象、188模型端口、162条可见候选连接；12主设施、六区域、22条外部候选线路保留。A1种薯、A2食用菌、B1番茄、B2草莓、C1水培与种苗、C2秋烘。

这是可审查的候选演示版。C2三换热器并联是新设计提案。端口是模型接点，现场喷嘴、独立设施配准、C1临水疑点、路网穿越、水力与现场工况仍待证据；Google Maps API、Jev在线视觉和生产迁移未完成。分析页仅C1绑定合成教学结果，其他对象保持无数据态。旧版资产随包保留来源，新页使用 integrated-v2/facilities.glb。

原始材料、密钥、node_modules 和服务日志没有放入本交付包。保留各底图原署名与来源说明；外部组件固定在 HTML 中的版本。

交付与下一步见 docs/DELIVERY_20261117.md、docs/NEXT_STEPS_20261117.md。M13公开地物复核数据与C1图在qc/m13-geographic-review-v1/；它尚未作为主页面业务图层接入。新结果显示C1模型场坪和P2回水候选线与公开红海子水体几何相交，必须独立核验；原模型和路线未平移。
'''
    if verification != ROOT/'qc/m12-connected-v1':
        instructions=instructions.replace('M12 连接整合版','M13 地理复核版（保留M12整合模型）').replace('它尚未作为主页面业务图层接入','顶部“地理复核”已接入主地图：293条观察可搜索、筛选、点击聚焦；Esc先返回列表，再退出；关闭恢复原视角和设施卡')
    if integrated['revision']=='m14-sensors-integrated-v1':
        instructions=instructions.replace('M13 地理复核版（保留M12整合模型）','M14 农业测点整合版')
        instructions=instructions.replace('outputs/m12-connected-v1/乌兰察布_连接整合场景_v1.blend',blend)
        instructions=instructions.replace('四农业图在 integrated-v1/','四农业父设施与测点细节图在 integrated-v3/')
        instructions=instructions.replace('integrated-v2/facilities.glb',integrated['asset_url'].removeprefix('../map-viewer/assets/'))
        instructions=instructions.replace('M13公开地物复核数据与C1图在qc/m13-geographic-review-v1/','当前公开地物复核数据与C1图在'+args.geographic_dir+'/')
        instructions+='\n四个农业SENSOR均有37个实体网格与独立同版图片。搜索AGRI_014_SENSOR、AGRI_015_SENSOR、AGRI_016_SENSOR或AGRI_017_SENSOR，点击索引查看。关闭子设备或按Esc先返回父设施，再关闭退出。仪表为未接管样件，无厂家、量程、实测读数或PLC信号接线，不能作为已投运设备。\n'
    (out/'使用说明.md').write_text(instructions)
    for name in ['launch.py','打开三维系统.command','使用说明.md']:
        inventory[name]=hashlib.sha256((out/name).read_bytes()).hexdigest()
    unexpected={str(p.relative_to(out)) for p in out.rglob('*') if p.is_file()}-set(inventory)-{'package-manifest.json'}
    assert not unexpected, f'Unexpected package files preserved for review: {sorted(unexpected)}'
    browser_path=verification/'package-browser-verification.json'
    browser=json.loads(browser_path.read_text()) if browser_path.exists() else None
    if browser:
        assert browser['status']=='pass' and browser['exit_code']==0
        for name,digest in browser.get('runtime_hashes',{}).items():
            assert inventory[name]==digest, f'Browser-tested package changed: {name}'
    receipt=dict(status='assembled_with_browser_verified_runtime' if browser else 'assembled_not_yet_browser_verified',files=len(inventory),sha256=inventory,
                 source_identity=str((verification/'tested-identity.json').relative_to(ROOT)),tested_code_head=identity['tested_head'],
                 browser_evidence=str(browser_path.relative_to(ROOT)) if browser else None,
                 browser_evidence_scope=browser.get('scope','85-object runtime, PTES preview, pipe highlight, Escape and close; metadata-only additions checked by file hashes') if browser else 'not_run',
                 external_dependencies=['Three.js CDN','MapLibre CDN'])
    (out/'package-manifest.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'output':str(out),'files':len(inventory),'copied_bytes':sum(p.stat().st_size for p in files)},ensure_ascii=False))


if __name__=='__main__':main()
