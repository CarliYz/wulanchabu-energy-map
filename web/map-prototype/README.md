# 当前三维地图工作台

这是当前用户入口。项目背景、全部操作说明、安装、地图来源、版本和工程边界统一见仓库根目录 [README](../../README.md)。

从根目录运行 `python3 launch.py` 自动打开空闲端口；开发固定入口为 `python3 web/map-prototype/serve.py`，地址 `http://127.0.0.1:8767/web/map-prototype/`。

当前 integrated-asset.json 指向 integrated-v3/facilities.glb，85 可选对象、188 模型端口和 162 条可见候选连接。A1种薯、A2食用菌、B1番茄、B2草莓；四农业仪表为未接管示意件。三底图分别使用 OSM/FOSSGIS、EOX Sentinel-2 和 Copernicus DEM，未接 Google API。

源码与数据合同见 [架构](../../docs/ARCHITECTURE.md)，当前公开版范围见 [发布说明](../../docs/PUBLIC_RELEASE.md)。模型制作需另行准备本地原始资料与 Blender 场景。
