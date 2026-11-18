import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { chromium } from '@playwright/test';

const projectRoot = fileURLToPath(new URL('../', import.meta.url));
const cli = fileURLToPath(new URL('../node_modules/@playwright/mcp/cli.js', import.meta.url));
const config = fileURLToPath(new URL('./mcp.config.json', import.meta.url));
const child = spawn(process.execPath, [cli, '--config', config, '--executable-path', chromium.executablePath()], { stdio: 'inherit', cwd: projectRoot });
child.on('error', error => { console.error('Playwright MCP launch failed:', error); process.exitCode = 1; });
child.on('exit', code => { process.exitCode = code ?? 1; });
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => child.kill(signal));
