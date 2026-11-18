import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {ORIGIN,forward,inverse,localToLonLat} from '../web/map-prototype/projection.mjs';
import {flowCoordinates} from '../web/map-prototype/energy-network.mjs';
import {waterPolygons,observeLine,observePad,waterLocation} from '../src/map_v2/public_geometry.mjs';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const output=path.resolve(root,process.argv[2]||'qc/m13-geographic-review-v1');fs.mkdirSync(output,{recursive:true});
const sourceDir=path.join(root,'qc/m11-integrated-v1/public-screening');
const read=p=>JSON.parse(fs.readFileSync(p));
const sha=p=>createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const source=read(path.join(sourceDir,'public-source-receipt.json'));
const routeFile=path.join(root,'data/map-v2/routes.json'),routes=read(routeFile).routes;
const registry=read(path.join(root,'web/map-prototype/facility-registry.json'));
const geographic=read(path.join(root,'data/map-v2/geographic-manifest.json'));
const displayPads=read(path.join(output,'display-pads.json'));
if(sha(path.join(root,displayPads.asset_path))!==displayPads.asset_sha256)throw new Error('Display pad asset identity changed');
const bounding=line=>[Math.min(...line.map(p=>p[0])),Math.min(...line.map(p=>p[1])),Math.max(...line.map(p=>p[0])),Math.max(...line.map(p=>p[1]))];
const lowerBound=(a,b)=>Math.hypot(Math.max(a[0]-b[2],b[0]-a[2],0),Math.max(a[1]-b[3],b[1]-a[3],0));
const threshold=30,categories={},features=[];
for(const kind of ['highway','railway','waterway','waterbody']) {
  const snapshot=source.snapshots[kind],file=path.join(sourceDir,snapshot.file);
  if(sha(file)!==snapshot.sha256)throw new Error(`Public source identity changed: ${kind}`);
  const raw=read(file);categories[kind]=[];
  if(raw.elements.length!==snapshot.elements)throw new Error(`Public source count changed: ${kind}`);
  for(const element of raw.elements) {
    const feature={id:`${element.type}/${element.id}`,kind,tags:element.tags||{},source_sha256:snapshot.sha256};
    if(kind==='waterbody')feature.polygons=waterPolygons(element,forward);
    else {
      if(!element.geometry||element.geometry.length<2)throw new Error(`Missing line geometry ${feature.id}`);
      feature.line=element.geometry.map(p=>{
        if(!Number.isFinite(p.lon)||!Number.isFinite(p.lat))throw new Error(`Invalid public point ${feature.id}`);
        return forward([p.lon,p.lat]);
      });
    }
    feature.bounds=bounding(feature.line||feature.polygons.flat(2));
    categories[kind].push(feature);features.push(feature);
  }
}
function screen(line,kind,isPad=false) {
  const bounds=bounding(line),ordered=categories[kind].map(feature=>({feature,lower:lowerBound(bounds,feature.bounds)})).sort((a,b)=>a.lower-b.lower);
  let nearest=null;const candidates=[];
  for(const {feature,lower} of ordered) {
    if(nearest&&lower>Math.max(threshold,nearest.distance_m))break;
    const observed=isPad?observePad(line,feature):observeLine(line,feature);
    const result={feature_id:feature.id,kind,tags:feature.tags,relation:observed.relation,
      ...(feature.polygons&&line.length===1?{anchor_location:waterLocation(line[0],feature.polygons)}:{}),
      distance_m:Number(observed.distance.toFixed(3)),boundary_distance_m:Number(observed.boundaryDistance.toFixed(3)),
      route_position:inverse(observed.onRoute),feature_position:inverse(observed.onFeature),source_sha256:feature.source_sha256};
    if(!nearest||observed.distance<nearest.distance_m)nearest=result;
    if(observed.distance<=threshold)candidates.push(result);
  }
  candidates.sort((a,b)=>a.distance_m-b.distance_m||a.feature_id.localeCompare(b.feature_id));
  return {status:candidates.some(c=>c.distance_m===0)?'overlap_observed':candidates.length?'nearby_observed':'no_feature_within_30m',threshold_m:threshold,nearest,candidates,
    engineering_status:'blocked',engineering_execution:'not_run'};
}
const toUTM=([x,y])=>[ORIGIN[0]+x,ORIGIN[1]+y];
const routeResults=routes.map(route=>({route_id:route.route_id,flow_from:route.flow_from,flow_to:route.flow_to,
  public_screening:Object.fromEntries(Object.keys(categories).map(kind=>[kind,screen(flowCoordinates(route).map(toUTM),kind)]))}));
const facilityResults=registry.objects.map(object=>{
  const feature=geographic.features.find(f=>f.id===object.object_id);
  if(!feature)throw new Error(`Missing facility anchor ${object.object_id}`);
  const pad=displayPads.pads.find(p=>p.object_id===object.object_id);
  if(!pad)throw new Error(`Missing display pad ${object.object_id}`);
  return {object_id:object.object_id,name:object.name,lonlat:localToLonLat(feature.xyz),geometry_scope:'anchor_and_actual_display_pad_not_surveyed_footprint',
    display_pad:{...pad,waterbody:screen(pad.ring_local_xy.map(toUTM),'waterbody',true)},
    public_screening:Object.fromEntries(Object.keys(categories).map(kind=>[kind,screen([toUTM(feature.xyz)],kind)]))};
});
const checks={input_identities:'pass',water_feature_retention:{raw:source.snapshots.waterbody.elements,parsed:categories.waterbody.length,relations:categories.waterbody.filter(f=>f.id.startsWith('relation/')).length},
  display_pad_water_intersection:'pass_for_model_geometry_only',independent_registration:'not_run',surveyed_footprint_water_intersection:'not_run',geoid_correction:'not_run',construction_route:'not_run'};
const report={revision:'m13-public-geographic-review-v1',created_at:new Date().toISOString(),tested_head:spawnSync('git',['rev-parse','HEAD'],{cwd:root,encoding:'utf8'}).stdout.trim(),
  source:{...source,route_input_sha256:sha(routeFile),facility_registry_sha256:sha(path.join(root,'web/map-prototype/facility-registry.json')),
    geographic_manifest_sha256:sha(path.join(root,'data/map-v2/geographic-manifest.json')),coordinate_method:'WGS84 to existing EPSG:32649 series; polygon topology and approximate metre distances, not an independent geodetic registration'},
  checks,route_results:routeResults,facility_results:facilityResults,
  limitations:['30m is a screening threshold, not engineering clearance.','OSM absence is not proof of absence.','Facility checks apply to seed anchors and actual display pads, not surveyed footprints.','Inside-water observations concern the public snapshot, not a determination of current legal shoreline.','Surveyed controls, tolerances, vertical correction, right-of-way and construction methods remain required.']};
const geojson={type:'FeatureCollection',attribution:'© OpenStreetMap contributors · ODbL',features:features.map(f=>({type:'Feature',properties:{id:f.id,kind:f.kind,...f.tags,source_sha256:f.source_sha256},
  geometry:f.line?{type:'LineString',coordinates:f.line.map(inverse)}:{type:'MultiPolygon',coordinates:f.polygons.map(poly=>poly.map(ring=>ring.map(inverse)))}}))};
fs.writeFileSync(path.join(output,'geographic-review.json'),JSON.stringify(report,null,2)+'\n');
fs.writeFileSync(path.join(output,'public-features.geojson'),JSON.stringify(geojson)+'\n');
const brief=s=>s.candidates.length?s.candidates.slice(0,3).map(c=>`${c.tags.name||c.tags.ref||'未命名'} ${c.feature_id} / ${c.distance_m}m`).join('；')+(s.candidates.length>3?`；另${s.candidates.length-3}项`:''):'本快照30m内未发现';
const markdown=[
  '# 公开地物与候选位置复核', '',
  '2026-11-17。四类原始快照2814个要素，22候选路线与12主设施全部复跑。水体28个（含3个多边形关系）完整保留；outer/inner、包含、岛屿与缺损几何分别处理。', '',
  '## 关键发现', '',
  'C1原锚点位于公开红海子水体外，距边界约6.262m；当前GLB的实际场坪顶点凸包与该公开水体相交。P2_V2_RETURN也与红海子公开几何相交，P2_V2_SUPPLY距最近水体约7.519m。没有修改模型或22条路线。', '',
  '旧M11筛查在relation无顶层geometry时提前跳过，漏读3关系；也未处理整段位于水面内部的情形。旧25/28红回归保留，当前28/28。此报告取代旧水域筛查结论；不同投影算法产生小幅筛查距离差异，不作为测量精度。', '',
  '![C1公开水体与模型场坪](c1-public-water-review.png)', '',
  '## 候选路线观察', '',
  '距离为近似米制筛查；0m表示公开几何相交/面内，30m仅为复核阈值。每格最多列3项，完整ID、标签、最近坐标、SHA见geographic-review.json。', '',
  '| 路线 | 道路 | 铁路 | 线状水域 | 水体面 |', '|---|---|---|---|---|',
  ...routeResults.map(r=>`| ${r.route_id} | ${Object.keys(categories).map(k=>brief(r.public_screening[k])).join(' | ')} |`), '',
  '## 主设施锚点与实际模型场坪', '',
  '| 主设施 | 锚点至最近水边 | 模型场坪观察 | 最近水体 |', '|---|---|---|---|',
  ...facilityResults.map(f=>`| ${f.object_id} ${f.name} | ${f.public_screening.waterbody.nearest.boundary_distance_m}m | ${f.display_pad.waterbody.status==='overlap_observed'?'与公开水体相交/包含':'30m内未发现/邻近，见JSON'} | ${f.display_pad.waterbody.nearest.tags.name||'未命名'} ${f.display_pad.waterbody.nearest.feature_id} |`), '',
  '## 判决与下一门', '',
  'Standards：原始快照SHA、要素计数、GLB实际顶点身份与失败路径通过本批检查。Spec：公开筛查数据和复核图完成；主页面覆盖层/逐条定位尚未实施，独立地理与工程验收仍blocked/not_run。审查模式coordinator_single_agent。', '',
  '锚点、场坪、现场建筑占地分别看待；本图不是现场岸线、地籍、用地许可或施工断面。水体孔洞被排除，未命中仍不证明不存在。独立控制点、测量容差、高程校正、工程路由与水力保持开放。下一步按docs/NEXT_STEPS_20261117.md将观察接入主地图，再依据专业输入决定路线调整。', '',
  `路线SHA256：${report.source.route_input_sha256}。模型SHA256：${displayPads.asset_sha256}。来源及时间戳在geographic-review.json/source，全部公开要素几何在public-features.geojson。© OpenStreetMap contributors · ODbL。`, ''
].join('\n');
fs.writeFileSync(path.join(output,'geographic-review.md'),markdown);
const escape=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
const c1=facilityResults.find(f=>f.object_id==='AGRI_018'),center=forward(c1.lonlat),radius=1500,scale=900/(radius*2);
const pixel=([x,y])=>[(x-center[0]+radius)*scale+40,(center[1]+radius-y)*scale+100];
const drawLine=line=>line.map((p,i)=>`${i?'L':'M'}${pixel(p).map(n=>n.toFixed(2)).join(',')}`).join(' ');
const viewport=[center[0]-radius,center[1]-radius,center[0]+radius,center[1]+radius];
const svg=[];
for(const feature of features.filter(f=>lowerBound(viewport,f.bounds)===0)) {
  if(feature.polygons)svg.push(`<path d="${feature.polygons.map(poly=>poly.map(ring=>drawLine(ring)+'Z').join(' ')).join(' ')}" fill="#d6eaf8" fill-rule="evenodd" stroke="#4898b7" stroke-width="1.3"/>`);
  else svg.push(`<path d="${drawLine(feature.line)}" fill="none" stroke="${feature.kind==='railway'?'#906b84':feature.kind==='waterway'?'#4898b7':'#c4c8ce'}" stroke-width="${feature.kind==='highway'?'2':'1'}"/>`);
}
for(const route of routes.filter(r=>r.route_id.startsWith('AGRI_018')))svg.push(`<path d="${drawLine(flowCoordinates(route).map(toUTM))}" fill="none" stroke="${route.route_id.endsWith('RETURN')?'#347cbe':'#bf681e'}" stroke-width="4" stroke-dasharray="9 6"/>`);
svg.push(`<path d="${drawLine(c1.display_pad.ring_local_xy.map(toUTM))}Z" fill="#dfb09a" fill-opacity="0.25" stroke="#b03a2e" stroke-width="3"/>`);
const nearest=c1.public_screening.waterbody.nearest;
const p=pixel(center);
svg.push(`<circle cx="${p[0]}" cy="${p[1]}" r="9" fill="#c13939" stroke="white" stroke-width="3"/><text x="${p[0]+15}" y="${p[1]-15}" font-size="19" fill="#8a2020">C1 候选锚点（原坐标）</text>`);
const locationLabel={water_area:'水体内',inner_exclusion:'非水面孔洞内',outside_outer:'水体外'}[nearest.anchor_location];
const padOverlap=c1.display_pad.waterbody.status==='overlap_observed';
const text=`${nearest.tags.name||'未命名水体'} ${nearest.feature_id}：锚点在${locationLabel}，距水边约${nearest.boundary_distance_m}m；场坪${padOverlap?'跨水体边界':'未见水体重叠'}。`;
fs.writeFileSync(path.join(output,'c1-public-water-review.svg'),`<svg xmlns="http://www.w3.org/2000/svg" width="980" height="1120" viewBox="0 0 980 1120"><rect width="980" height="1120" fill="white"/><text x="40" y="38" font-size="25" font-family="sans-serif">C1 候选位置与公开水体复核</text><text x="40" y="70" font-size="14" font-family="sans-serif">${escape(text)}</text><defs><clipPath id="map"><rect x="40" y="100" width="900" height="900"/></clipPath></defs><g clip-path="url(#map)"><rect x="40" y="100" width="900" height="900" fill="#f7f8fa"/>${svg.join('')}</g><g font-family="sans-serif" font-size="14" fill="#414751"><text x="40" y="1032">蓝色：公开水体；红框：模型场坪；橙/蓝虚线：原候选供回线。上北，3km × 3km。</text><text x="40" y="1061">© OpenStreetMap contributors · ODbL · 快照2026-11-17；场坪不是现场建筑占地，水域未经测量核定。</text><text x="40" y="1090">没有移动模型；独立控制点、高程校正、地籍与工程路线仍待验收。</text></g></svg>`);
console.log(JSON.stringify({routes:routeResults.length,facilities:facilityResults.length,public_features:features.length,checks,c1_water:nearest},null,2));
