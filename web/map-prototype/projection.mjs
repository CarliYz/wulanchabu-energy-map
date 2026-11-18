// WGS84 / UTM zone 49N, Snyder transverse Mercator series (no datum shift).
// Local X/Y are UTM grid east/north, not true east/north.
const A = 6378137, F = 1 / 298.257223563, K = 0.9996;
const E2 = F * (2 - F), EP2 = E2 / (1 - E2), RAD = Math.PI / 180;
export const ORIGIN = Object.freeze([687361.2359406124, 4540425.231254176, 1200]);
export function forward([lon, lat]) {
  const phi = lat * RAD, s = Math.sin(phi), c = Math.cos(phi), t = Math.tan(phi);
  const n = A / Math.sqrt(1 - E2 * s * s), T = t * t, C = EP2 * c * c;
  const q = c * (lon - 111) * RAD;
  const M = A * ((1 - E2 / 4 - 3 * E2 ** 2 / 64 - 5 * E2 ** 3 / 256) * phi
    - (3 * E2 / 8 + 3 * E2 ** 2 / 32 + 45 * E2 ** 3 / 1024) * Math.sin(2 * phi)
    + (15 * E2 ** 2 / 256 + 45 * E2 ** 3 / 1024) * Math.sin(4 * phi)
    - 35 * E2 ** 3 / 3072 * Math.sin(6 * phi));
  return [500000 + K * n * (q + (1 - T + C) * q ** 3 / 6
    + (5 - 18 * T + T * T + 72 * C - 58 * EP2) * q ** 5 / 120),
  K * (M + n * t * (q * q / 2 + (5 - T + 9 * C + 4 * C * C) * q ** 4 / 24
    + (61 - 58 * T + T * T + 600 * C - 330 * EP2) * q ** 6 / 720))];
}
export function inverse([east, north]) {
  const e1 = (1 - Math.sqrt(1 - E2)) / (1 + Math.sqrt(1 - E2));
  const mu = north / K / (A * (1 - E2 / 4 - 3 * E2 ** 2 / 64 - 5 * E2 ** 3 / 256));
  const phi = mu + (3 * e1 / 2 - 27 * e1 ** 3 / 32) * Math.sin(2 * mu)
    + (21 * e1 ** 2 / 16 - 55 * e1 ** 4 / 32) * Math.sin(4 * mu)
    + 151 * e1 ** 3 / 96 * Math.sin(6 * mu) + 1097 * e1 ** 4 / 512 * Math.sin(8 * mu);
  const s = Math.sin(phi), c = Math.cos(phi), t = Math.tan(phi);
  const N = A / Math.sqrt(1 - E2 * s * s), R = A * (1 - E2) / (1 - E2 * s * s) ** 1.5;
  const T = t * t, C = EP2 * c * c, d = (east - 500000) / (N * K);
  const lat = phi - N * t / R * (d * d / 2 - (5 + 3 * T + 10 * C - 4 * C * C - 9 * EP2) * d ** 4 / 24
    + (61 + 90 * T + 298 * C + 45 * T * T - 252 * EP2 - 3 * C * C) * d ** 6 / 720);
  const lon = 111 * RAD + (d - (1 + 2 * T + C) * d ** 3 / 6
    + (5 - 2 * C + 28 * T - 3 * C * C + 8 * EP2 + 24 * T * T) * d ** 5 / 120) / c;
  return [lon / RAD, lat / RAD];
}
// MapLibre uses the spherical Mercator circumference (6371008.8m radius).
const CIRCUMFERENCE = 2 * Math.PI * 6371008.8;
export function mercator([lon, lat], height = 0) {
  return [(lon + 180) / 360,
    (1 - Math.log(Math.tan(Math.PI / 4 + lat * RAD / 2)) / Math.PI) / 2,
    height / (CIRCUMFERENCE * Math.cos(lat * RAD))];
}
export const ORIGIN_LONLAT = inverse(ORIGIN);
export const MERCATOR_ORIGIN = mercator(ORIGIN_LONLAT);
export const WORLD_SCALE = 1 / (CIRCUMFERENCE * Math.cos(ORIGIN_LONLAT[1] * RAD));
export function localToLonLat([x, y]) { return inverse([ORIGIN[0] + x, ORIGIN[1] + y]); }
export function glbToLocal([x, y, z]) { return [x, -z, y]; }
export function localToWorld(local) {
  const m = mercator(localToLonLat(local), local[2]);
  return [(m[0] - MERCATOR_ORIGIN[0]) / WORLD_SCALE,
    (m[1] - MERCATOR_ORIGIN[1]) / WORLD_SCALE, m[2] / WORLD_SCALE];
}
export function glbToWorld(glb) { return localToWorld(glbToLocal(glb)); }
