# 当前工作台交互测试

当前隔离配置是 e2e.closeout.config.js，默认测试端口18867（ENERGY_QA_PORT可更改），自动启停自己的服务，拒绝复用其他工作区的服务；不会接管已有8767。

```sh
cd qa/agent-e2e
npm ci
npx playwright install chromium
E2E_TELEMETRY_DISABLED=1 npx e2e run --config e2e.closeout.config.js
```

完整 CLI 参数以锁定版本的 npx e2e --help 为准。九个既有文件与runtime-closeout.e2e.js共同覆盖当前场景。e2e.config.js / viewer.e2e.js 和根目录 Playwright 默认配置是历史 viewer，不能混算为当前新版验收。当前命令及证据语义见docs/QA_CURRENT.md。

Jev preflight：node jev-preflight.mjs。缺 TYPESAFE_AI_API_KEY 时明确退出2，不发起模型调用。凭据仅经进程环境提供，不写入仓库。全局 MCP 注册不随克隆自动完成；查看演示不需要 MCP。

历史 M14 的96种行为为分组通过证据；本次发布是否复跑以根目录 qc/public-release-verification.json 为准。
