import { web } from '@e2e-dev/web';

export default {
  projectId: 'wulanchabu-energy-map',
  targets: [{
    name: 'desktop',
    engine: web({ viewport: { width: 1440, height: 900 } }),
    app: { url: process.env.ENERGY_QA_URL || 'http://127.0.0.1:8766/' },
  }],
  tests: 'tests/**/*.e2e.js',
  workers: 1,
  retries: 0,
  timeout: 60000,
  actionTimeout: 10000,
  assertionTimeout: 4000,
  output: '.e2e',
  reporters: ['list', 'markdown'],
};
