import { spawn, execFileSync } from 'node:child_process';
import { createInterface } from 'node:readline';
import { mkdir, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

process.chdir(fileURLToPath(new URL('../', import.meta.url)));

const child = spawn(process.execPath, [fileURLToPath(new URL('./mcp-server.mjs', import.meta.url))], { stdio: ['pipe', 'pipe', 'pipe'] });
const waiting = new Map();
const log = [];
const stderr = [];
let sequence = 0;
child.stderr.on('data', chunk => stderr.push(chunk.toString()));
const lines = createInterface({ input: child.stdout });
lines.on('line', line => {
  const message = JSON.parse(line);
  if (!message.id) return;
  const waiter = waiting.get(message.id);
  if (!waiter) return;
  waiting.delete(message.id);
  clearTimeout(waiter.timer);
  if (message.error) waiter.reject(new Error(JSON.stringify(message.error)));
  else waiter.resolve(message.result);
});
child.on('exit', code => {
  for (const item of waiting.values()) { clearTimeout(item.timer); item.reject(new Error(`MCP exited ${code}`)); }
  waiting.clear();
});
function request(method, params) {
  const id = ++sequence;
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => { waiting.delete(id); reject(new Error(`MCP timeout: ${method}`)); }, 45000);
    waiting.set(id, { resolve, reject, timer });
    child.stdin.write(JSON.stringify({ jsonrpc: '2.0', id, method, params }) + '\n');
  });
}
async function call(name, args) {
  const result = await request('tools/call', { name, arguments: args });
  log.push({ tool: name, arguments: args, result });
  if (result.isError) throw new Error(`${name}: ${JSON.stringify(result.content)}`);
  return result;
}
let pass = false;
try {
  const initialized = await request('initialize', { protocolVersion: '2024-11-05', capabilities: {}, clientInfo: { name: 'energy-map-qa', version: '0.2.0' } });
  log.push({ initialized });
  child.stdin.write(JSON.stringify({ jsonrpc: '2.0', method: 'notifications/initialized' }) + '\n');
  const list = await request('tools/list', {});
  log.push({ tools: list.tools.map(t => t.name) });
  await call('browser_navigate', { url: process.env.ENERGY_QA_URL || 'http://127.0.0.1:8766/' });
  await call('browser_wait_for', { textGone: '正在加载 Blender 三维模型…' });
  const snapshot = await call('browser_snapshot', {});
  const snapshotText = snapshot.content.filter(c => c.type === 'text').map(c => c.text).join('\n');
  if (!snapshotText.includes('乌兰察布能源优先区')) throw new Error('Viewer entry absent from MCP snapshot');
  const auditLine = snapshotText.split('\n').find(line => /button .*审计与系统状态/.test(line) || /button "☷"/.test(line));
  const ref = auditLine?.match(/\[ref=([^\]]+)\]/)?.[1];
  if (!ref) throw new Error('Audit button absent from MCP snapshot');
  await call('browser_click', { target: ref, element: '审计与系统状态' });
  const audit = await call('browser_snapshot', {});
  if (!JSON.stringify(audit).includes('代码与页面版本')) throw new Error('Audit did not open');
  await call('browser_press_key', { key: 'Escape' });
  // Escape is an audited product requirement, not a smoke-pass assumption.
  await call('browser_snapshot', {});
  await call('browser_close', {});
  pass = true;
} finally {
  child.stdin.end();
  child.kill();
  lines.close();
  await mkdir('qc/ui-v4', { recursive: true });
  const head = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim();
  await writeFile('qc/ui-v4/mcp-toolchain-smoke.json', JSON.stringify({ capturedAt: new Date().toISOString(), baseHead: head, scope: 'MCP handshake, live viewer navigation, audit open, Escape sent; product Escape verdict belongs to e2e', pass, log, stderr }, null, 2) + '\n');
}
console.log('MCP toolchain smoke passed; product acceptance is separate.');
