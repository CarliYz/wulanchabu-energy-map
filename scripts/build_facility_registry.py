"""Create runtime metadata from the live Blender export; never rewrite frozen fixtures."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
read = lambda p: json.loads((ROOT / p).read_text())
export = read('web/map-viewer/assets/facilities-v1/export-receipt.json')
geo = read('data/map-v2/geographic-manifest.json')
names = {
    'DC_004': ('DC1', '华为云数据中心', 'dc', '余热候选接口；建筑为体量代理，未取得机房实测与接入协议。'),
    'DC_005': ('DC2', '阿里巴巴数据中心', 'dc', '余热候选接口；建筑为体量代理，未取得机房实测与接入协议。'),
    'DC_006': ('DC3', '益武堂数据中心组团', 'dc', '算力组团体量代理；源水经隔离换热后供给候选热路。'),
    'HUB_011': ('热泵', 'CO₂跨临界热泵枢纽', 'energy', '源侧水、站内CO₂制冷剂、用户水分回路；近端隔离直供与远端提温分别规划。CO₂为闭合制冷循环，不向温室输送CO₂气体。'),
    'STORE_012': ('PTES', 'PTES池式储热', 'energy', '日/周调节的池式储热；半盖剖面为表达示意，规划50万m³并不等于当前几何容量。'),
    'DEMO_013': ('A3', '独立CO₂冷热与土壤储热科研', 'a', '独立5–10MW科研示范，抬升土壤剖面用来展示换热U管，不能读取为实际埋深。'),
    'AGRI_014': ('A1', '种薯组培与原原种温室', 'a', '组培楼与原原种温室分设；利用近端低品位热进行环境温控。'),
    'AGRI_015': ('A2', '工厂化食用菌', 'a', '保温菌房、菌架及空气处理设备的代表模型；生产温湿度和能耗待核。'),
    'AGRI_016': ('B1', '冬季番茄连栋温室', 'b', '吊蔓温室与分拣集配建筑；用户水温度、负荷和水力设计仍待核。'),
    'AGRI_017': ('B2', '冬春草莓高架温室', 'b', '高架栽培与温室支路代表模型；候选中段接入尚未落实。'),
    'AGRI_018': ('C1', '叶菜水培与冷凉种苗', 'c', '两组温室分设热水与营养液循环，板换、泵阀、PLC和测点已补入示意模型；C1原坐标保留，临水疑点待核。'),
    'DRY_019': ('C2', '秋季低温烘干中心', 'c', '燕麦与脱水蔬菜秋烘；料仓、输送廊道、热风换热器和提温模块。50–55℃热风需另行提温。'),
}
objects = []
for item in export['objects']:
    fid = item['object_id']
    short, name, group, description = names[fid]
    feature = next(f for f in geo['features'] if f['id'] == fid)
    props = item['properties']
    area = props.get('planned_area_m2_range')
    if area is None and 'planned_area_m2' in props:
        area = [props['planned_area_m2']] * 2
    objects.append({'object_id': fid, 'name': name, 'short_name': short, 'group': group,
                    'description': description, 'installation_status': '候选规划 · 位置与接入待核',
                    'planning_area': None if area is None else {'min': area[0], 'max': area[1], 'unit': 'm2'},
                    'model_footprint_m2': item['model_footprint_m2'], 'model_root_xyz': item['root_xyz'],
                    'model_revision': props.get('m8_revision', 'geographic-v2-representative'),
                    'source': feature['properties']['source'], 'gaps': ['未取得设施级独立定位', '尚无实测工况与热潜力结果', '非厂家采购或施工模型'],
                    'preview_url': f'../map-viewer/assets/facilities-v1/{fid}.png',
                    'gltf_root_index': item['gltf_root_index']})
registry = {'revision': 'facilities-runtime-v1', 'source_export': 'web/map-viewer/assets/facilities-v1/export-receipt.json',
            'asset_url': '../map-viewer/assets/facilities-v1/facilities.glb', 'sha256': export['sha256'],
            'sources': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in
                        ['data/map-v2/geographic-manifest.json', 'docs/UI_DESIGN_PLAN_V2.md']},
            'objects': objects}
(ROOT / 'web/map-prototype/facility-registry.json').write_text(json.dumps(registry, ensure_ascii=False, indent=2) + '\n')
print(f'Runtime registry: {len(objects)} semantic roots; frozen fixtures unchanged')
