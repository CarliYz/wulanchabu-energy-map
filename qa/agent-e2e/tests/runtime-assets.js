import { readFileSync } from 'node:fs';

const base = new URL('../../../web/map-prototype/', import.meta.url);
export function currentFacilityAsset() {
  const manifest = JSON.parse(readFileSync(new URL('integrated-asset.json', base), 'utf8'));
  return {
    manifest,
    pattern: '**/' + manifest.asset_url.replace(/^(\.\.\/)+/, ''),
    readBytes: () => readFileSync(new URL(manifest.asset_url, base)),
  };
}
