# 单文件 HTML 交付

当前候选演示版可以直接双击打开：

`outputs/releases/乌兰察布能源地图-单文件-v0.3.0-rc.4.html`

该文件内嵌了当前工作台运行所需的地图数据、三维 GLB、设施图片、复核数据和运行模块。浏览器需要联网加载固定版本的 Three.js 和 MapLibre CDN；如果网络受限，请使用同版本目录的 `launch.py` 启动完整本地 HTTP 包。GitHub Release 会将该 HTML 作为附件提供，避免把约 86 MB 的二进制文件写入普通 Git 历史。

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
