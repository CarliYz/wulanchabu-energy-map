# 架构与业务合同

目标：在同一地理空间内关联设施、模型、回路、公开地物和分析来源。

## 运行结构

浏览器通过本地 HTTP 读取 `web/map-prototype/index.html`，由 `app.mjs` 组织 MapLibre 地图与 Three.js 自定义层；不要求后端数据库。`launch.py` 只监听 127.0.0.1 并自动选择空闲端口。

实体来源为 facility-registry、c1-runtime、ab-terminal-runtime 和 m10-system-runtime 四份注册表。`integrated-asset.json` 固定当前 GLB 和实体节点；`asset-bindings.json` 保留地形资产。map-viewer 是历史入口，当前工作台复用其 assets。

索引、模型拾取、地图标签、属性、图片和关系共用 object_id。选择触发高亮与取景；子设备关闭返回父设施；父设施关闭恢复地图操作。地理复核详情先退出到列表，再恢复进入前的视角、对象与底图。

## 回路合同

C1（AGRI_018）包含热水、营养液和控制三类关系；热水与营养液各有独立闭合路径，不能因介质标签相近而混接换热器两侧。CO₂ 循环限定在 HUB 站内；供暖水、电输入和能量传递分别表达。PTES 充放热支路有独立回水，初态 IDLE，模型不允许据此执行现场充放热。端口是模型接点，未证明现场喷嘴位置。

A1=种薯、A2=食用菌、B1=番茄、B2=草莓；四农业仪表保留未接管 / 无实测状态。C2 三换热器并联为候选设计提案。

## 数据与不确定性

分析按 object_id + scenario_id + hour_index 绑定。只有 C1 绑定合成教学结果，其他对象无数据；unknown 与 0 分开。教学数据不能改标成 measured，候选几何不能改标成 operational_verified。来源合同需包含具名路径、性质和 SHA-256。

坐标合同为 EPSG:32649，原点及 Blender / GLB 轴转换见 data/contracts/coordinate-contract.json。地图投影往返通过不等于独立地理配准通过。C1 场坪、P2 回水候选线与公开水域相交观察保留，不通过平移模型消除疑点。

## 制作与验收

Blender 制作脚本与导出脚本在 src/map_v2；GLB、图卡、注册表和来源哈希需要同步更新。部分制作脚本依赖未分发的本机场景或历史证据，需配置 BASE 并补齐原始资料；公共版本优先保证现成网页可运行。

Node / Python 测试验证关系、状态、合同和教学计算；真实浏览器检查验证加载、点击、聚焦与退出。历史 M14 / M15 的验证范围与本次公共快照复验分开记录。公共发布不关闭独立工程验收、现场数据或生产迁移任务。
