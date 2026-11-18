import { access, stat } from 'node:fs/promises';
import { basename, dirname, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const configPath = fileURLToPath(new URL('./e2e.map-prototype.config.js', import.meta.url));
const { default: config } = await import(configPath);
const repositoryRoot = resolve(fileURLToPath(new URL('../../', import.meta.url)));
const expected = [
  'map-prototype.e2e.js',
  'c1-devices.e2e.js',
  'energy-paths.e2e.js',
  'analysis-audit.e2e.js',
  'ab-terminals.e2e.js',
  'm10-system-devices.e2e.js',
  'integrated-model.e2e.js',
];

if (!Array.isArray(config.tests) || config.tests.length !== expected.length) {
  throw new Error(`E2E_CONFIG_TEST_COUNT: expected ${expected.length} explicit test files`);
}

const actual = config.tests.map((testPath) => basename(testPath));
if (actual.join('|') !== expected.join('|')) {
  throw new Error(`E2E_CONFIG_TEST_SET: expected ${expected.join(', ')}, got ${actual.join(', ')}`);
}

for (const testPath of config.tests) {
  if (testPath.startsWith('/')) throw new Error(`E2E_CONFIG_TEST_PATH_ABSOLUTE: ${testPath}`);
  if (/[!*?[\]]/.test(testPath)) throw new Error(`E2E_CONFIG_GLOB_LEFT: ${testPath}`);
  const resolvedTestPath = resolve(dirname(configPath), testPath);
  await access(resolvedTestPath);
  if (!(await stat(resolvedTestPath)).isFile()) throw new Error(`E2E_CONFIG_TEST_NOT_FILE: ${testPath}`);
  if (!relative(repositoryRoot, resolvedTestPath).startsWith('qa/agent-e2e/tests/')) {
    throw new Error(`E2E_CONFIG_TEST_OUTSIDE_EXPECTED_ROOT: ${testPath}`);
  }
}

const target = config.targets?.[0];
if (target?.app?.command?.cwd !== repositoryRoot) {
  throw new Error(`E2E_CONFIG_APP_CWD: expected ${repositoryRoot}, got ${target?.app?.command?.cwd}`);
}
if (target.app.command.args.join(' ') !== 'web/map-prototype/serve.py') {
  throw new Error('E2E_CONFIG_APP_COMMAND: map prototype server command changed');
}

console.log(JSON.stringify({
  status: 'pass',
  config: configPath,
  discovered_test_files: config.tests.length,
  test_files: config.tests,
  app_cwd: target.app.command.cwd,
  app_command: target.app.command.args,
}));
