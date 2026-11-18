# 当前工作台的验证入口

Node 需要 `^22.22.3` 或 `>=24.8.0`，Python 合同建议3.12。查看演示只需 Python3 和运行依赖CDN网络；测试另外安装锁定依赖。

```sh
npm ci
node --test tests/*.test.mjs
python3 -m pip install -r requirements-contracts.txt
python3 -m unittest discover -s tests -p 'test_*.py'
python3 scripts/refresh_runtime_audit.py
cd qa/agent-e2e
npm ci
npx playwright install chromium
E2E_TELEMETRY_DISABLED=1 npx e2e run --config e2e.closeout.config.js
```

隔离配置运行九个既有行为文件及 `runtime-closeout.e2e.js`，默认端口18867，可用 `ENERGY_QA_PORT` 改到空闲端口。服务只绑定127.0.0.1；runner负责启停，不接管用户8767实例，端口冲突应失败。输出目录 `.e2e-m16` 保存报告/失败trace。无需模型密钥，未调用Jev；确定性浏览器测试不等于模型视觉判决。

根目录 `npm run qa:current` 调用上述当前入口；`npm run qa` 保留历史 viewer 测试，不能用旧入口通过代替新版验收。单文件过滤后的跳过用例不算通过；检查report.json里的selected、status及exitCode。

M16新增16条覆盖：无对象/未绑定对象的分析空态、C1教学时段、审计正反向Tab与Escape（优先关闭当前浮层、保留背景菜单）、来源失败/重新读取/真实JSON下载、1440×900/1100×800/760×600的分析与详情遮挡及地理复核退出、axe严重/致命问题。设备网格真实拾取、图片解码、三底图和故障路径继续由原九个文件覆盖。

`refresh_runtime_audit.py`默认只检查源码与审计SHA；审阅变更后显式 `--write` 刷新。公共分发还需 `verify_public_release.py` 核对清单及模型绑定。GitHub Actions在公共快照运行相同检查；是否已通过以实际Actions回执为准，配置文件存在不代表CI成功。

Standards与Spec由协调者分阶段判定，当前没有独立worker。软件回归不代替独立工程验收；C1/P2水域相交、测点接管、真实时序、Google/Jev及生产环境仍按各自输入放行。Figma原型的更多路径/响应式不由网页测试自动覆盖。
