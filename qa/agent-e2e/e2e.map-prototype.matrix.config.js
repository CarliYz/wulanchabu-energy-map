import { web } from '@e2e-dev/web';

export default {
  projectId: 'wulanchabu-map-prototype-matrix',
  targets: [
    { name: 'wide-1440', engine: web({ viewport: { width: 1440, height: 1000 } }), app: { url: 'http://127.0.0.1:8767/web/map-prototype/' } },
    { name: 'mid-1100', engine: web({ viewport: { width: 1100, height: 900 } }), app: { url: 'http://127.0.0.1:8767/web/map-prototype/' } },
    { name: 'narrow-760', engine: web({ viewport: { width: 760, height: 900 } }), app: { url: 'http://127.0.0.1:8767/web/map-prototype/' } },
  ],
  tests: ['tests/analysis-audit.e2e.js'],
  workers: 1,
  retries: 0,
  timeout: 60000,
  actionTimeout: 10000,
  assertionTimeout: 5000,
  output: '.e2e-map-prototype-matrix',
  reporters: ['list', 'markdown'],
};
