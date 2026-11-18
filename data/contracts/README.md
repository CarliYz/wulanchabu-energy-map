# 能源地图共享合同 v1

本目录是 M6（01A-344）的可执行合同。产品实现继续按 `docs/UI_DESIGN_PLAN_V2.md` 放行；合同测试不代表浏览器或 Blender 已修复。

`objects.schema.json` 定义唯一 object_id；asset_id 只是显式别名。parent_id 形成无环树。规划面积、代表模型占地、几何边界分别存储；未知为 null，不补零。installation_status 与 model_status 独立，不能从地图位置或模型存在推导已投运。

`ports.schema.json` 定义对象、介质、进出方向、回路、局部坐标空间。`connections.schema.json` 仅允许同回路同介质的 out→in 连接。板换/气冷器的跨回路能量传递单列 energy_transfers，禁止把它当流体连接。CO₂ 端口仅归属站内对象；PTES 保留直达 C1 路径以外的充放支路。热水与营养液两组温室支路分别闭合。

fixtures 是用于构建和负例校验的最小设计集合：21 个对象、6 个回路、62 个端口、32 条拟接边。子设备位置为 null、模型状态 missing、边状态 not_built；不能作为端口几何连续或模型完整的证据。C1 的 190×150m 是旧代表场坪，不是已建/规划面积；实际模型边界须由模型 Builder 整体计算并填 focus_bounds。

`results.schema.json` 用 scenario_id + object_id + timestamp/hour_index 绑定结果，记录单位、数据性质、输入和参数哈希。旧 48 行数据保留 unbound。绑定的教学样例仅进入 DEMO_USER，C1 明确 missing_inputs/null。入口必须先校验 bundle；读取时按精确 ID/工况/时间过滤，不能拿全局教学结果填空。旧结果转换在本批只提供 fixture，尚未迁移生产分析代码。

`coordinate-contract.json` 固定 EPSG:4326 → EPSG:32649 → 局部米制 → Blender Z-up → GLB Y-up。EGM2008 正高不能直接当地图椭球高；大地水准面改正和 map_world_matrix 留待地图原型核定。三旧点仅是投影自检，独立配准仍 not_run；M9 必须另交 qc/map-registration.json。

`viewer-state.schema.json`、`fixtures/viewer-state.json` 和 `web/map-viewer/viewer-state.mjs` 冻结状态与转换接口。树和地图都发送 select(object_id)，同一个 selectedObjectId 驱动高亮、整体聚焦、右卡和结果请求。请求同时携带选择修订、请求修订、对象、工况和时间；旧响应与旧失败都被丢弃。这个模块已单测，尚未接入现有 index.html；实际相机、画布拾取、焦点归还和窄屏遮挡在 M9 验收。

Escape 每次只退出一层：图片/审计→图层浮层→详情子页→设施卡→分析→搜索→索引→工具。关闭卡片清选中并保留相机；复位及撤销、原生下拉优先级、拖动取消由 UI Builder 接入 DOM/相机适配器。按键动作不动画；鼠标抽屉以 180–240ms transform/opacity 为目标，并支持 reduced-motion。

验证（Python 3.9+，Node 18+）：

```sh
python3 -m venv .venv-contracts
.venv-contracts/bin/python -m pip install -r requirements-contracts.txt
.venv-contracts/bin/python scripts/validate_contracts.py
.venv-contracts/bin/python -m unittest discover -s tests -v
node --test tests/viewer-state.test.mjs
```

schema 验证结构，validate_contracts.py 另查来源哈希、引用、父级循环、介质/回路隔离、站内 CO₂、结果单位和绑定。来源变更必须重新核对其具体字段再更新哈希；不要为了让测试通过自动接受新来源。Independent Standards / Spec 审查、Figma 往返及运行时 QA 各自记录，不互相替代。
