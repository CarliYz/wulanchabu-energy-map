# 第三方数据与组件说明

## 地图和高程

| 来源 | 本仓库用途 | 条款与署名 |
| --- | --- | --- |
| OpenStreetMap / FOSSGIS | 标准地图归档图、公开道路 / 铁路 / 水域要素 | © OpenStreetMap contributors；OSM 数据按 ODbL，保留 FOSSGIS 原图署名；归档图不是无限缩放地图服务 |
| EOxCloudless / EOX IT Services GmbH | Sentinel-2 2024 卫星图和模型纹理 | CC BY-NC-SA 4.0；contains modified Copernicus Sentinel data 2024；保留署名、非商业及相同方式共享要求 |
| Copernicus DEM GLO-30 | 地形网格 / 数据 DEM 视图 | 源自 Copernicus DEM，EGM2008 正高；保留 geographic-manifest 中的数据来源、版本及原许可声明 |

来源定位：`data/map-v2/geographic-manifest.json`、`design/m7/map-assets/map-design-sources.json`、`qc/m14-sensors-integrated-v1/geography/`。几何筛查结果来自公开地图，不能代替测量成果。

来源官网：

- OpenStreetMap：https://www.openstreetmap.org/copyright
- EOxCloudless：https://s2maps.eu/
- Copernicus DEM：https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM

原始第三方报告、Google 地图截图、用户上传 ZIP / DOCX / PDF 和参考视频均不作为本公共仓库素材分发。公共模型中的卫星纹理仍适用上述影像条款。

## 软件依赖

Three.js 0.180.0（MIT）和 MapLibre GL JS 5.6.1（BSD-3-Clause）从 CDN 加载。Playwright、axe、e2e 等开发依赖以各包自带许可证为准，版本记录在各 package-lock.json；node_modules 不提交。依赖的许可不构成本仓库自有代码的授权。

## 自有代码和模型

本次只将仓库设置为公开，未选定自有代码的开源许可证。未加入 MIT / Apache 等统一许可证；使用或再分发时需分别确认自有代码授权和地图素材条款。
