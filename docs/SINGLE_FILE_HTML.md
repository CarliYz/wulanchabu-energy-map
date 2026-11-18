# 单文件 HTML 交付

当前候选演示版可以直接双击打开：

`outputs/releases/energy-map-workbench-single-v0.3.0-rc.4.html`

该文件内嵌了当前工作台运行所需的地图数据、三维 GLB、设施图片、复核数据和运行模块。浏览器需要联网加载固定版本的 Three.js 和 MapLibre CDN；完整本地 HTTP 包同样需要这些 CDN。GitHub Release 将脱敏公开快照生成的 HTML 作为附件提供，约 82 MB。下载后可用随附 `SHA256SUMS.txt` 核对文件；发布名使用英文，避免托管服务改写中文名称。原本地中文命名副本可以保留。

重新生成：

```sh
python3 scripts/build_single_file_html.py
```

也可以显式指定版本和输出路径：

```sh
python3 scripts/build_single_file_html.py --version 0.3.0-rc.4 \
  --output outputs/releases/乌兰察布能源地图-单文件-v0.3.0-rc.4.html
```

当前文件已通过 `file://` 浏览器检查：地图初始化、85 个实体标签、三底图切换、索引展开、设施详情卡和 Escape 退出均可用。
