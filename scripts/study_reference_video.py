# -*- coding: utf-8 -*-
"""Index every decoded reference frame and build review contact sheets.

Run after ffmpeg extraction of the primary video stream with passthrough fps.
This produces research evidence only and does not edit product assets.
"""
import argparse
import csv
import hashlib
import json
import math
import subprocess
from fractions import Fraction
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageStat

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/reference-study-20261116"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--source", type=Path, required=True, help="Original local reference video")
parser.add_argument("--verify-only", action="store_true", help="Verify existing evidence without rewriting it")
args = parser.parse_args()
SOURCE = args.source.resolve(strict=True)
frames = sorted((OUT / "frames").glob("frame_*.jpg"))
probe = json.loads(subprocess.check_output([
    "ffprobe", "-v", "error", "-select_streams", "v:0",
    "-show_streams", "-show_frames", "-show_entries",
    "stream=width,height,avg_frame_rate,duration,nb_frames:frame=best_effort_timestamp_time",
    "-of", "json", str(SOURCE),
]))
stream = probe["streams"][0]
rate = Fraction(stream["avg_frame_rate"])
if rate <= 0 or rate.denominator != 1:
    raise ValueError("Contact sheets require a positive integer constant frame rate")
fps = int(rate)
resolution = [int(stream["width"]), int(stream["height"])]
duration = float(stream["duration"])
timestamps = [float(f["best_effort_timestamp_time"]) for f in probe["frames"]]
if not frames or len(frames) != len(timestamps):
    raise RuntimeError(f"Frame count mismatch: {len(frames)}, {len(timestamps)}")
if stream.get("nb_frames", "N/A") != "N/A" and len(frames) != int(stream["nb_frames"]):
    raise RuntimeError("Decoded frame count differs from the primary stream")
if abs(timestamps[0]) > 1e-5 or any(abs(t - i / fps) > 1e-5 for i, t in enumerate(timestamps)):
    raise ValueError("Viewer requires zero-origin constant-rate timestamps; source differs")
if abs(duration - len(frames) / fps) > 1e-5:
    raise ValueError("Primary stream duration differs from decoded timestamps")
source_sha256 = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
if args.verify_only:
    manifest = json.loads((OUT / "video-manifest.json").read_text())
    actual = {"source_sha256": source_sha256, "frame_count": len(frames),
              "fps": fps, "duration_seconds": duration, "resolution": resolution}
    for key, value in actual.items():
        if manifest[key] != value:
            raise RuntimeError(f"Video identity differs: {key}")
    with (OUT / "frame-index.csv").open(newline="") as f:
        indexed = list(csv.DictReader(f))
    if len(indexed) != len(frames):
        raise RuntimeError("Frame index is incomplete")
    for i, (path, row, timestamp) in enumerate(zip(frames, indexed, timestamps), 1):
        if (int(row["frame"]) != i or row["file"] != str(path.relative_to(ROOT))
                or abs(float(row["timestamp_seconds"]) - timestamp) > 1e-5
                or row["sha256"] != hashlib.sha256(path.read_bytes()).hexdigest()):
            raise RuntimeError(f"Frame evidence differs: {i}")
        with Image.open(path) as image:
            if list(image.size) != resolution:
                raise RuntimeError(f"Frame resolution differs: {i}")
    if manifest["frame_index_sha256"] != hashlib.sha256((OUT / "frame-index.csv").read_bytes()).hexdigest():
        raise RuntimeError("Frame index digest differs")
    print(json.dumps({"status": "pass", "read_only": True, **actual}, ensure_ascii=False))
    raise SystemExit(0)
rows = []
prev = None
for i, (path, timestamp) in enumerate(zip(frames, timestamps), 1):
    with Image.open(path) as im:
        small = im.convert("RGB").resize((160, 90))
    delta = None if prev is None else sum(ImageStat.Stat(ImageChops.difference(small, prev)).mean) / 3
    rows.append({"frame": i, "timestamp_seconds": timestamp,
                 "file": str(path.relative_to(ROOT)),
                 "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                 "mean_rgb_delta_160x90": delta})
    prev = small
with (OUT / "frame-index.csv").open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

def sheet(indices, filename, width, columns):
    height = round(width * resolution[1] / resolution[0])
    cell_height = height + 18
    image = Image.new("RGB", (width * columns, cell_height * ((len(indices) + columns - 1) // columns)), "#e5e7eb")
    draw = ImageDraw.Draw(image)
    for n, index in enumerate(indices):
        x, y = (n % columns) * width, (n // columns) * cell_height
        with Image.open(frames[index]) as original:
            image.paste(original.resize((width, height)), (x, y))
        draw.text((x + 3, y + height + 1), f"F{index+1:04d} {timestamps[index]:.3f}s", fill="black")
    image.save(OUT / "sheets" / filename, quality=93)

sheet(list(range(0, len(frames), fps)), "overview-1fps.jpg", 256, 5)
for second in range(math.ceil(duration)):
    indices = list(range(second * fps, min((second + 1) * fps, len(frames))))
    if indices:
        sheet(indices, f"second-{second:02d}-all-frames.jpg", 256, 5)
for start in range(0, len(frames), fps * 5):
    end = min(start + fps * 5, len(frames))
    sheet(list(range(start, end)), f"all-{start//fps:02d}-{end/fps:04.1f}s.jpg", 160, 10)
manifest = {
    "source_path": str(SOURCE), "source_sha256": source_sha256,
    "frame_count": len(frames), "fps": fps, "duration_seconds": duration,
    "resolution": resolution, "first_timestamp": timestamps[0], "last_timestamp": timestamps[-1],
    "extraction": "ffmpeg primary stream 0:v:0, fps_mode passthrough, JPEG q:v 2",
    "index": str((OUT / "frame-index.csv").relative_to(ROOT)),
    "frame_index_sha256": hashlib.sha256((OUT / "frame-index.csv").read_bytes()).hexdigest(),
    "coverage": "Every decoded primary-stream frame collected; contact sheets include all frames. Visual interpretation is recorded separately.",
}
(OUT / "video-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
print(json.dumps(manifest, ensure_ascii=False))
