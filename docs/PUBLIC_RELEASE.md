# 公共发布 v0.3.0-rc.1

2026-11-18。用户明确要求推送当前代码、整理背景与操作说明，并公开 GitHub 仓库；随后确认目标账号为当前已登录的 **CarliYz**。

目标仓库：`CarliYz/wulanchabu-energy-map`。这是独立三维地图项目，保留已有 Energy-System / Energy-System-v2.0 仓库。

## 来源与版本

- 本地来源分支：codex/energy-map-v2。
- 发布准备前代码提交：100ca65e2f3b1acc1627ca4a4e9646188c64127e。
- 当前运行模型：m14-sensors-integrated-v1；设计同步：M15。
- 设施 GLB SHA-256：aa00fa4c3502197f77851c3a2eb6617875462862c0bbd7351ceeaf4c0cf1869f。
- 公共初始历史使用经检查的当前快照，不导入含原始上传材料的本地历史。

## 分发范围

包含当前与历史 viewer 源码、运行 GLB / 图片、地理数据、三种地图资源、Blender 制作脚本、数据合同、Node / Python / e2e 测试、启动器和公共使用说明。

不包含 inputs、research 原件、用户上传 ZIP / DOCX / PDF / 视频、私人操作日志、全量 QC 截图批次、凭据、node_modules、原生 .blend 或本机完整 Git 历史。需要的公开地理数据和一份用于合同测试的历史缺陷样本保留。

公共导出会将制作脚本中的个人工作目录前缀换为 `/path/to/wulanchabu-energy-map`，保留“需自行设置 BASE”的事实；合同测试 PLAN 来源改指公共架构说明、历史样本只去除个人路径，再更新其 SHA。网页实际执行模块、GLB、地图和当前业务数据保持来源字节。转换和逐文件哈希在 public-release-manifest.json 中登记。

## 启动与验证

README 是面向使用者的统一入口。launch.py 的动态端口不影响开发 / e2e 的固定 8767 入口。公共快照复验记录在 qc/public-release-verification.json；审查为协调者单代理 Standards / Spec 分轴检查，不宣称独立 QA。

GitHub 公共版本是候选演示预发行版。既有地理、工程、真实数据、Google / Jev、联合验收和生产部署缺口保持开放。
