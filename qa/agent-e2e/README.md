# 当前工作台交互测试

当前配置是 e2e.map-prototype.config.js，固定入口 http://127.0.0.1:8767/web/map-prototype/，会按配置启动 / 复用该服务。源码与运行 URL 必须来自同一仓库。

```sh
cd qa/agent-e2e
npm ci
npx playwright install chromium
E2E_TELEMETRY_DISABLED=1 npx e2e run --config e2e.map-prototype.config.js
```

测试按文件分组执行以适应工具超时。完整 CLI 参数以锁定版本的 npx e2e --help 为准。map-prototype、c1-devices、energy-paths、analysis-audit、ab-terminals、m10-system-devices、integrated-model、geographic-review、agriculture-sensors 分别覆盖当前场景。e2e.config.js / viewer.e2e.js 和根目录 Playwright 默认配置是历史 viewer，不能混算为当前新版验收。

Jev preflight：node jev-preflight.mjs。缺 TYPESAFE_AI_API_KEY 时明确退出2，不发起模型调用。凭据仅经进程环境提供，不写入仓库。全局 MCP 注册不随克隆自动完成；查看演示不需要 MCP。

历史 M14 的96种行为为分组通过证据；本次发布是否复跑以根目录 qc/public-release-verification.json 为准。
