# -*- coding: utf-8 -*-
"""Build a local frame-by-frame research viewer from already extracted evidence."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/reference-study-20261116'
manifest = json.loads((OUT / 'video-manifest.json').read_text())
chapters = json.loads((ROOT / 'research/reference-study-20261116/video-observations.json').read_text())
html = '''<!doctype html>
<html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>参考视频逐帧研究 · 乌兰察布能源地图</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#f4f5f6;color:#172127;font:15px/1.6 system-ui,sans-serif}header,main{max-width:1480px;margin:auto;padding:18px 24px}h1{font-size:23px;margin:0}p{margin:8px 0}small{color:#53606a}.layout{display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:18px}.stage,aside{background:white;border:1px solid #dce1e5;border-radius:8px;padding:14px}.stage img{display:block;width:100%;height:auto;background:#ddd}button,select,input{font:inherit}button,select{padding:7px 11px;background:white;border:1px solid #b8c2ca;border-radius:5px;cursor:pointer}button:disabled{opacity:.4;cursor:default}button:focus-visible,select:focus-visible,input:focus-visible{outline:2px solid #1666ae;outline-offset:2px}.controls{display:flex;gap:7px;align-items:center;flex-wrap:wrap;margin:14px 0}input[type=range]{width:100%}.tag{font-size:12px;color:#30634a}a{color:#165d91}h2{font-size:18px;margin:14px 0 6px}h3{font-size:14px;margin:14px 0 4px}.notice{border-left:3px solid #b7c4cf;padding-left:12px}#frame-label{font-variant-numeric:tabular-nums}select{width:100%}@media(max-width:900px){.layout{grid-template-columns:1fr}header,main{padding:14px}}
</style>
<header><h1>参考视频逐帧研究</h1><p>Mirror of Nature → 乌兰察布算热储与农业地图工作台</p><small>完整采集1935帧 · 30fps · 64.5秒 · 原图1280×720。联系表覆盖全部帧，关键转场另看原图；不声称逐张全分辨率人工阅读。</small></header>
<main><div class="layout"><section class="stage"><a id="original" target="_blank" rel="noreferrer"><img id="frame" alt="参考视频原始帧"></a><div class="controls"><button id="prev-second">前1秒</button><button id="prev">上一帧</button><button id="next">下一帧</button><button id="next-second">后1秒</button><strong id="frame-label" aria-live="polite"></strong></div><input id="scrub" aria-label="视频帧" type="range" min="1" max="1935" value="1" step="1"><small>左右键逐帧，Shift＋左右键前后1秒。点击图像查看原分辨率。视频中的剪辑/淡出不等于真实按钮操作。</small></section><aside><span class="tag">研究观察与设计迁移建议</span><h2>章节</h2><select id="chapter" aria-label="研究章节"></select><h2 id="title"></h2><h3>可见内容</h3><p id="observed"></p><h3>业务理解及证据边界</h3><p id="interpretation"></p><h3>用于本项目</h3><p id="application"></p><p class="notice">只借布局与交互层级。航班、风场、天气和视频中的数值不进入本项目业务。研究查看器不代表产品已重构。</p><p><a href="sheets/overview-1fps.jpg" target="_blank">1fps导航总览</a> · <a href="frame-index.csv">完整帧索引与哈希</a> · <a href="video-manifest.json">视频身份</a></p></aside></div></main>
<script>
const chapters=__CHAPTERS__;const total=__TOTAL__;const fps=__FPS__;
const $=id=>document.getElementById(id);let current=1;
chapters.forEach((c,i)=>{const o=document.createElement('option');o.value=i;o.textContent=`${c.start.toFixed(3)}s · ${c.title}`;$('chapter').append(o)});
function show(n){current=Math.min(total,Math.max(1,Number(n)));const t=(current-1)/fps;const file=`frames/frame_${String(current).padStart(6,'0')}.jpg`;$('frame').src=file;$('original').href=file;$('frame').alt=`第${current}帧，${t.toFixed(3)}秒`;$('scrub').value=current;$('frame-label').textContent=`F${String(current).padStart(6,'0')} / ${total} · ${t.toFixed(3)}s`;const i=Math.max(0,chapters.findIndex(c=>t>=c.start&&t<c.end));$('chapter').value=i;for(const key of ['title','observed','interpretation','application'])$(key).textContent=chapters[i][key];$('prev').disabled=current===1;$('prev-second').disabled=current===1;$('next').disabled=current===total;$('next-second').disabled=current===total}
$('prev').onclick=()=>show(current-1);$('next').onclick=()=>show(current+1);$('prev-second').onclick=()=>show(current-fps);$('next-second').onclick=()=>show(current+fps);$('scrub').oninput=e=>show(e.target.value);$('chapter').onchange=e=>show(Math.ceil(chapters[e.target.value].start*fps)+1);document.addEventListener('keydown',e=>{if(['SELECT','INPUT'].includes(e.target.tagName))return;if(e.key==='ArrowLeft'||e.key==='ArrowRight'){e.preventDefault();show(current+(e.key==='ArrowRight'?1:-1)*(e.shiftKey?fps:1))}});show(1);
</script></html>'''
html = html.replace('__CHAPTERS__', json.dumps(chapters, ensure_ascii=False)).replace('__TOTAL__', str(manifest['frame_count'])).replace('__FPS__', str(manifest['fps']))
(OUT / 'index.html').write_text(html)
print(OUT / 'index.html')
