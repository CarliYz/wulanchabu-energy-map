import fs from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { REVIEW_SOURCE } from '../web/map-prototype/geographic-review-source.mjs';

const root = new URL('../', import.meta.url);
const hash = path => createHash('sha256').update(fs.readFileSync(new URL(path, root))).digest('hex');
const reportPath = REVIEW_SOURCE.report.url.replace(/^\.\.\/\.\.\//, '');
const geometryPath = REVIEW_SOURCE.features.url.replace(/^\.\.\/\.\.\//, '');
if (!reportPath.startsWith('qc/') || !geometryPath.startsWith('qc/')) throw new Error('Geographic sources must remain repository QC artifacts');
if (hash(reportPath) !== REVIEW_SOURCE.report.sha256 || hash(geometryPath) !== REVIEW_SOURCE.features.sha256) throw new Error('Geographic audit source identity mismatch');
const path = new URL('web/map-prototype/audit-manifest.json', root), audit = JSON.parse(fs.readFileSync(path));
if (audit.web_model.sha256 !== REVIEW_SOURCE.assetSha256) throw new Error('Geographic audit model identity mismatch');
const revision = REVIEW_SOURCE.revision;
audit.runtime_revision = revision;
if (!audit.requirement_revision.includes('M13-public-geographic-review')) audit.requirement_revision += '+M13-public-geographic-review';
audit.generated_at = new Date().toISOString();
const items = [
  ['公开地物复核报告', reportPath, '293条公开观察·工程blocked'],
  ['公开地物几何', geometryPath, '2814个公开地物·28个水体含3关系'],
  ['实际模型场坪提取', reportPath.replace(/[^/]+$/, 'display-pads.json'), '12模型场坪·非现场占地'],
  ['地图地理复核交互', 'web/map-prototype/geographic-review.mjs', 'M13界面·独立工程核验未执行'],
  ...['highway', 'railway', 'waterway', 'waterbody'].map(kind => [`公开地物原始快照 ${kind}`, `qc/m11-integrated-v1/public-screening/public-${kind}-2026-11-17.json`, '2026-11-17 OSM快照·非现场测量'])
];
const paths = new Set(items.map(item => item[1]));
const labels = new Set(items.map(item => item[0]));
audit.source_inventory = audit.source_inventory.filter(item => !paths.has(item.path) && !labels.has(item.label));
audit.source_inventory.push(...items.map(([label, path, status_label]) => ({ label, path, version: revision, sha256: hash(path), status: 'candidate', status_label })));
const limit = 'M13公开快照观察：C1模型场坪及P2回水候选线与红海子水体几何相交；原坐标未移动，独立测量与工程核验仍未执行。';
if (!audit.limitations.includes(limit)) audit.limitations.push(limit);
fs.writeFileSync(path, JSON.stringify(audit, null, 2) + '\n');
console.log(JSON.stringify({ path: fileURLToPath(path), revision, added_or_refreshed: items.length }));
