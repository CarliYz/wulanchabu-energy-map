import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import { web } from '@e2e-dev/web';

const configDir = dirname(fileURLToPath(import.meta.url));
const repositoryRoot = resolve(configDir, '../..');
const testFiles = [
  'map-prototype.e2e.js',
  'c1-devices.e2e.js',
  'energy-paths.e2e.js',
  'analysis-audit.e2e.js',
  'ab-terminals.e2e.js',
  'm10-system-devices.e2e.js',
  'integrated-model.e2e.js',
  'geographic-review.e2e.js',
  'agriculture-sensors.e2e.js',
];

export default {
  projectId: 'wulanchabu-map-prototype',
  targets: [{
    name: 'desktop',
    engine: web({ viewport: { width: 1440, height: 1000 } }),
    app: {
      url: 'http://127.0.0.1:8767/web/map-prototype/',
      command: {
        executable: 'python3',
        args: ['web/map-prototype/serve.py'],
        cwd: repositoryRoot,
        log: resolve(configDir, 'full-e2e-app-server.log'),
        startupTimeout: 10000,
        shutdownTimeout: 3000,
        reuseExisting: true,
      },
    },
  }],
  tests: testFiles.map((name) => `tests/${name}`),
  workers: 1,
  retries: 0,
  timeout: 60000,
  actionTimeout: 10000,
  assertionTimeout: 5000,
  output: resolve(configDir, '.e2e-map-prototype'),
  reporters: ['list', 'markdown'],
};
