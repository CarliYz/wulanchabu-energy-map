import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import base from './e2e.map-prototype.config.js';

const configDir = dirname(fileURLToPath(import.meta.url));
const repositoryRoot = resolve(configDir, '../..');
const port = Number(process.env.ENERGY_QA_PORT || 18867);
if (!Number.isInteger(port) || port < 1024 || port > 65535) throw new Error('Invalid ENERGY_QA_PORT');

export default {
  ...base,
  projectId: 'wulanchabu-runtime-closeout',
  targets: base.targets.map(target => ({ ...target, app: {
    url: `http://127.0.0.1:${port}/web/map-prototype/`,
    command: {
      executable: 'python3',
      args: ['-u', '-m', 'http.server', String(port), '--bind', '127.0.0.1', '--directory', repositoryRoot],
      cwd: repositoryRoot,
      log: resolve(configDir, '.e2e-m16/server.log'),
      reuseExisting: false,
      startupTimeout: 10000,
      shutdownTimeout: 3000,
    },
  } })),
  tests: [...base.tests, 'tests/runtime-closeout.e2e.js'],
  output: resolve(configDir, '.e2e-m16'),
};
