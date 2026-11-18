import { spawn, execFileSync } from 'node:child_process';
import { createInterface } from 'node:readline';
import { mkdir, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('./', import.meta.url));
process.chdir(root);
const output = new URL('../../outputs/reference-study-20261116/e2e-mcp-smoke.json', import.meta.url);
const child = spawn(process.execPath, [
  fileURLToPath(new URL('node_modules/e2e/dist/cli/bin.js', import.meta.url)),
  'mcp', '--config', fileURLToPath(new URL('e2e.config.js', import.meta.url)),
], {
  cwd: fileURLToPath(new URL('../../', import.meta.url)), stdio: ['pipe', 'pipe', 'pipe'],
  env: { ...process.env, E2E_TELEMETRY_DISABLED: '1' },
});
const log = [];
const errors = [];
const waiting = new Map();
let sequence = 0;
let session;
let pass = false;
let failure;
const lines = createInterface({ input: child.stdout });
child.stderr.on('data', b => errors.push(b.toString()));
lines.on('line', line => {
  let message;
  try { message = JSON.parse(line); }
  catch (error) { errors.push(`Non-JSON stdout: ${line}`); return; }
  const waiter = waiting.get(message.id);
  if (!waiter) return;
  waiting.delete(message.id);
  clearTimeout(waiter.timer);
  if (message.error) waiter.reject(new Error(JSON.stringify(message.error)));
  else waiter.resolve(message.result);
});
child.on('exit', code => {
  for (const entry of waiting.values()) {
    clearTimeout(entry.timer);
    entry.reject(new Error(`e2e MCP exited ${code}`));
  }
  waiting.clear();
});
function request(method, params) {
  return new Promise((resolve, reject) => {
    const id = ++sequence;
    const timer = setTimeout(() => { waiting.delete(id); reject(new Error(`Timeout: ${method}`)); }, 55000);
    waiting.set(id, { resolve, reject, timer });
    child.stdin.write(JSON.stringify({ jsonrpc: '2.0', id, method, params }) + '\n');
  });
}
async function call(name, args) {
  const result = await request('tools/call', { name, arguments: args });
  log.push({ name, args, result });
  if (result.isError) throw new Error(`${name}: ${JSON.stringify(result.content)}`);
  return result;
}
try {
  log.push({ initialized: await request('initialize', {
    protocolVersion: '2024-11-05', capabilities: {},
    clientInfo: { name: 'energy-map-e2e-smoke', version: '0.1.0' },
  }) });
  child.stdin.write(JSON.stringify({ jsonrpc: '2.0', method: 'notifications/initialized' }) + '\n');
  const catalog = await request('tools/list', {});
  log.push({ catalog });
  const opened = await call('open_session', { target: 'desktop', headed: process.env.ENERGY_QA_HEADED === '1' });
  const joined = opened.content.filter(x => x.type === 'text').map(x => x.text).join('\n');
  console.log(joined);
  // The observed session identifier is read from the server response, never invented.
  session = opened.structuredContent?.sessionId || opened.structuredContent?.session;
  await call('tools', {});
  const observed = await call('call', { tool: 'observe', args: {} });
  if (!JSON.stringify(observed).includes('乌兰察布能源优先区')) throw new Error('Live observation is missing the expected viewer title: 乌兰察布能源优先区');
  await call('call', { tool: 'run_code', args: {
    code: 'await screen.getByText("正在加载 Blender 三维模型…").waitFor({state: "hidden", timeout: 30000});',
    timeout: 35000,
  } });
  await call('call', { tool: 'run_code', args: {
    code: 'await screen.getByRole("button", "☷").tap();\nawait expect(screen.getByText("代码与页面版本")).toBeVisible();',
    timeout: 30000,
  } });
  console.log('Live model ready; audit opened and its content observed.');
  pass = true;
} catch (error) {
  failure = error.message;
  process.exitCode = 1;
} finally {
  try { await call('close_session', session ? { session } : {}); }
  catch (error) { errors.push(`close_session: ${error.message}`); pass = false; failure ??= error.message; process.exitCode = 1; }
  child.stdin.end();
  child.kill();
  lines.close();
  await mkdir(new URL('../../outputs/reference-study-20261116/', import.meta.url), { recursive: true });
  await writeFile(output, JSON.stringify({
    capturedAt: new Date().toISOString(),
    baseHead: execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim(),
    scope: 'Official e2e stdio handshake and live viewer observation; not product acceptance',
    pass, failure, log, stderr: errors,
  }, null, 2) + '\n');
  console.log(JSON.stringify({ pass, failure, receipt: fileURLToPath(output) }));
}
