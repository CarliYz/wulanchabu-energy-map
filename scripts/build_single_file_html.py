"""Build a direct-open, single-file HTML copy of the current energy map workbench.

The normal release is still the preferred path for production-like review because it
keeps assets separate. This artifact embeds the runtime data and binary assets so a
user can double-click one HTML file. Three.js and MapLibre remain pinned CDN
dependencies, matching the public release contract.
"""

from __future__ import annotations

import base64
import argparse
import json
import mimetypes
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def package_version() -> str:
    return json.loads((ROOT / "package.json").read_text(encoding="utf-8"))["version"]

RUNTIME_MODULES = [
    "web/map-prototype/projection.mjs",
    "web/map-prototype/workspace-layout.mjs",
    "web/map-prototype/facility-index.mjs",
    "web/map-prototype/c1-relations.mjs",
    "web/map-prototype/ab-relations.mjs",
    "web/map-prototype/m10-graph.mjs",
    "web/map-prototype/m10-relations.mjs",
    "web/map-prototype/geographic-review-source.mjs",
    "web/map-prototype/geographic-review.mjs",
    "web/map-prototype/energy-network.mjs",
    "web/map-prototype/analysis-runtime.mjs",
    "web/map-prototype/app.mjs",
]

SEED_ASSETS = [
    "data/map-v2/geographic-manifest.json",
    "data/map-v2/routes.json",
    "data/contracts/coordinate-contract.json",
    "web/map-viewer/assets/analysis-results.json",
    "qc/m14-sensors-integrated-v1/geography/geographic-review.json",
    "qc/m14-sensors-integrated-v1/geography/public-features.geojson",
    "qc/m14-sensors-integrated-v1/geography/display-pads.json",
    "design/m7/map-assets/standard-base.png",
    "web/map-viewer/assets/乌兰察布_真实地理场景_v2.glb",
    "web/map-viewer/assets/integrated-v3/facilities.glb",
]

EMBED_GLBS = {
    "web/map-viewer/assets/乌兰察布_真实地理场景_v2.glb",
    "web/map-viewer/assets/integrated-v3/facilities.glb",
}


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def add_existing(files: set[str], path: Path) -> bool:
    if not path.is_file() or path.is_symlink():
        return False
    key = rel(path)
    if path.suffix.lower() in {".blend", ".tif", ".tiff"}:
        return False
    if path.suffix.lower() == ".glb" and key not in EMBED_GLBS:
        return False
    if key in files:
        return False
    files.add(key)
    return True


def resolve_candidate(value: str, source: Path) -> Path | None:
    if value.startswith(("http://", "https://", "data:", "blob:", "file:")):
        return None
    if len(value) > 300 or any(token in value for token in ("[", "]", "(", ")", "{", "}")):
        return None
    value = value.split("?", 1)[0].split("#", 1)[0]
    candidates = [source.parent / value, ROOT / value.lstrip("./")]
    for candidate in candidates:
        try:
            candidate = candidate.resolve()
            candidate.relative_to(ROOT)
        except ValueError:
            continue
        try:
            if candidate.is_file():
                return candidate
        except OSError:
            continue
    return None


def collect_assets() -> list[str]:
    files: set[str] = set()
    for value in SEED_ASSETS:
        add_existing(files, ROOT / value)
    for value in RUNTIME_MODULES:
        add_existing(files, ROOT / value)
    for path in (ROOT / "web/map-prototype").glob("*.json"):
        add_existing(files, path)
    for value in re.findall(
        r"[\"'](\.{1,2}/[^\"']+\.(?:json|geojson|png|glb))[\"']",
        (ROOT / "web/map-prototype/geographic-review-source.mjs").read_text(encoding="utf-8"),
    ):
        candidate = resolve_candidate(value, ROOT / "web/map-prototype/geographic-review-source.mjs")
        if candidate:
            add_existing(files, candidate)

    changed = True
    while changed:
        changed = False
        for key in list(files):
            path = ROOT / key
            if path.suffix.lower() not in {".json", ".geojson"}:
                continue
            try:
                document = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                continue

            def walk(value: object) -> None:
                nonlocal changed
                if isinstance(value, dict):
                    for child in value.values():
                        walk(child)
                elif isinstance(value, list):
                    for child in value:
                        walk(child)
                elif isinstance(value, str) and ("/" in value or "." in value):
                    candidate = resolve_candidate(value, path)
                    if candidate and add_existing(files, candidate):
                        changed = True

            walk(document)
    return sorted(files)


def build_module_data_urls() -> str:
    memo: dict[str, str] = {}

    def build(path: str) -> str:
        if path in memo:
            return memo[path]
        source = (ROOT / path).read_text(encoding="utf-8")
        source = source.replace(
            "'../../design/m7/map-assets/standard-base.png'",
            "globalThis.__ENERGY_STANDARD_MAP_URL__",
        )
        source = source.replace(
            "return JSON.parse(raw);",
            "return globalThis.__inlinePreviewRefs(JSON.parse(raw));",
        )
        source = source.replace(
            "from 'three';",
            "from 'https://cdn.jsdelivr.net/npm/three@0.180.0/build/three.module.js';",
        )
        source = source.replace(
            "from 'three/addons/utils/BufferGeometryUtils.js';",
            "from 'https://cdn.jsdelivr.net/npm/three@0.180.0/examples/jsm/utils/BufferGeometryUtils.js';",
        )
        source = source.replace(
            "from 'three/addons/loaders/GLTFLoader.js';",
            "from 'https://cdn.jsdelivr.net/npm/three@0.180.0/examples/jsm/loaders/GLTFLoader.js';",
        )

        def replace_relative(match: re.Match[str]) -> str:
            quote, specifier = match.group(1), match.group(2)
            clean = specifier.split("?", 1)[0]
            current = (ROOT / Path(path).parent / clean).resolve()
            target = rel(current)
            return f"from {quote}{build(target)}{quote}"

        source = re.sub(
            r"from\s+(['\"])(\.{1,2}/[^'\"]+\.mjs(?:\?[^'\"]*)?)\1",
            replace_relative,
            source,
        )
        encoded = base64.b64encode(source.encode("utf-8")).decode("ascii")
        url = f"data:text/javascript;base64,{encoded}"
        memo[path] = url
        return url

    return build("web/map-prototype/app.mjs")


def strip_module_imports(source: str) -> str:
    """Kept for compatibility with older local callers; the builder now uses data modules."""
    source = re.sub(r"^\s*import[^;]+;\s*\n", "", source, flags=re.MULTILINE)
    source = re.sub(r"\bexport\s+(?=(?:const|let|var|function|class)\b)", "", source)
    source = source.replace(
        "'../../design/m7/map-assets/standard-base.png'",
        "__ENERGY_STANDARD_MAP_URL__",
    )
    source = source.replace(
        "return JSON.parse(raw);",
        "return __inlinePreviewRefs(JSON.parse(raw));",
    )
    return source


def make_embedded_assets(paths: list[str]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for key in paths:
        path = ROOT / key
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        result[key] = {
            "mime": mime,
            "data": base64.b64encode(path.read_bytes()).decode("ascii"),
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default=None, help="Release version; defaults to package.json")
    parser.add_argument("--output", type=Path, default=None, help="Output HTML path")
    args = parser.parse_args()
    version = args.version or package_version()
    out = (args.output or (ROOT / "outputs" / "releases" / f"乌兰察布能源地图-单文件-v{version}.html")).resolve()
    assets = collect_assets()
    embedded = make_embedded_assets(assets)
    index = (ROOT / "web/map-prototype/index.html").read_text(encoding="utf-8")
    style = (ROOT / "web/map-prototype/style.css").read_text(encoding="utf-8")
    body_match = re.search(
        r"(<div id=\"map\".*?)(?=<script>\s*window\.m9BootErrors)",
        index,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not body_match:
        raise RuntimeError("Could not extract workbench body")
    body = re.sub(r"<script\b[^>]*>.*?</script>", "", body_match.group(1), flags=re.IGNORECASE | re.DOTALL)
    app_module_url = build_module_data_urls()
    asset_json = json.dumps(embedded, ensure_ascii=False, separators=(",", ":"))
    standard = embedded["design/m7/map-assets/standard-base.png"]

    bootstrap = f"""
globalThis.__ENERGY_EMBEDDED = {asset_json};
globalThis.__ENERGY_STANDARD_MAP_URL__ = "data:{standard['mime']};base64,{standard['data']}";
const __ENERGY_NATIVE_FETCH = globalThis.fetch.bind(globalThis);
function __energyKey(input) {{
  const raw = typeof input === 'string' ? input : input?.url;
  if (!raw || /^(?:https?:|data:|blob:|file:)/.test(raw)) return null;
  try {{
    return decodeURIComponent(new URL(raw, 'https://energy-map.invalid/web/map-prototype/').pathname.slice(1));
  }} catch {{ return null; }}
}}
function __energyBytes(entry) {{
  const binary = atob(entry.data);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes;
}}
function __energyResponse(key) {{
  const entry = globalThis.__ENERGY_EMBEDDED[key];
  if (!entry) return null;
  return new Response(__energyBytes(entry), {{ status: 200, headers: {{ 'Content-Type': entry.mime }} }});
}}
globalThis.fetch = (input, init) => __energyResponse(__energyKey(input)) || __ENERGY_NATIVE_FETCH(input, init);
function __inlinePreviewRefs(value, key = '') {{
  if (Array.isArray(value)) return value.map(item => __inlinePreviewRefs(item, key));
  if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).map(([name, item]) => [name, __inlinePreviewRefs(item, name)]));
  if (typeof value === 'string' && /preview|image|thumbnail/i.test(key)) {{
    const assetKey = __energyKey(value);
    const entry = assetKey && globalThis.__ENERGY_EMBEDDED[assetKey];
    if (entry && entry.mime.startsWith('image/')) return `data:${{entry.mime}};base64,${{entry.data}}`;
  }}
  return value;
}}
globalThis.__inlinePreviewRefs = __inlinePreviewRefs;
await import("{app_module_url}");
"""

    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>乌兰察布区域能源三维地图工作台 · 单文件版</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/maplibre-gl@5.6.1/dist/maplibre-gl.css">
<script type="importmap">{{"imports":{{"three":"https://cdn.jsdelivr.net/npm/three@0.180.0/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.180.0/examples/jsm/"}}}}</script>
<style>{style}</style>
</head>
<body>
{body}
<script>
window.m9BootErrors = [];
window.addEventListener('error', event => {{
  const message = event.message || `依赖加载失败: ${{event.target?.src || event.target?.href || 'unknown'}}`;
  window.m9BootErrors.push(message);
  document.getElementById('errors').textContent = message;
}}, true);
window.addEventListener('unhandledrejection', event => {{
  const message = String(event.reason?.stack || event.reason);
  window.m9BootErrors.push(message);
  document.getElementById('errors').textContent = message;
}});
</script>
<script src="https://cdn.jsdelivr.net/npm/maplibre-gl@5.6.1/dist/maplibre-gl.js"></script>
<script type="module">
{bootstrap}
</script>
</body>
</html>
"""
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    total = out.stat().st_size
    print(json.dumps({"status": "pass", "output": str(out), "bytes": total, "embedded_files": len(assets), "version": version}, ensure_ascii=False))


if __name__ == "__main__":
    main()
