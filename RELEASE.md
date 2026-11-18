# 乌兰察布能源三维地图 v0.3.0-rc.4

这是可本地运行的候选方案演示包。它包含 HTML / Three.js / MapLibre 工作台、Blender 导出的 GLB、三种底图、设施详情、候选关系、分析空态和审计入口。

## 启动

在本目录执行：

```sh
python3 launch.py
```

也可以直接执行：

```sh
python3 web/map-prototype/serve.py
```

然后访问终端打印的本机地址。不要用 `file://` 直接双击 `index.html`，因为模型和 JSON 需要 HTTP 服务读取。单文件 HTML 另见 `docs/SINGLE_FILE_HTML.md`，并随 GitHub Release 提供。

入口文件：`web/map-prototype/index.html`。

## 运行条件

Python 3、支持 WebGL 的桌面浏览器，以及固定版本 Three.js / MapLibre CDN 网络。查看演示不需要 Blender、Node.js 或 MCP。

## 版本证据

- 源提交：`1fd2598`
- 本文件由导出器生成，不代表已经执行测试。
- 当前运行测试命令与范围：`docs/QA_CURRENT.md`。
- 实际 CI 结果：<https://github.com/CarliYz/wulanchabu-energy-map/actions>。
- 本版本发行回执与附件校验：<https://github.com/CarliYz/wulanchabu-energy-map/releases/tag/v0.3.0-rc.4> 中的 `release-verification.json` 和 `SHA256SUMS.txt`。
- 可执行发布包校验：`python3 scripts/verify_public_release.py`。

## 当前边界

这是候选方案与数据关系演示。独立控制点、岸线/地籍、管网许可与水力、四测点真实 PLC 接管、真实时序、Google Maps API、Jev 在线视觉验证和生产迁移仍需后续输入与验收。
