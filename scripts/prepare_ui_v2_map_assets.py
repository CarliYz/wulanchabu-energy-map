"""Prepare georeferenced design backgrounds from existing project data.

Small, cached OSM preview only. These are Figma design assets, not a replacement
for the interactive viewer or surveyed engineering geometry.
"""
import hashlib
import json
import math
import argparse
from pathlib import Path
from urllib.request import Request, urlopen

import numpy as np
import rasterio
from rasterio.transform import from_bounds
from rasterio.warp import reproject, Resampling
from pyproj import Transformer
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--offline', action='store_true', help='Show an explicit unavailable standard-map state; never invent streets')
parser.add_argument('--standard-provider', choices=['osm', 'osmde'], default='osm')
parser.add_argument('--output', type=Path, default=ROOT / 'outputs/ui-v2')
args = parser.parse_args()
OUT = args.output
CACHE = ROOT / ('work/ui-v2-osm-cache' if args.standard_provider == 'osm' else 'work/ui-v3-osmde-cache')
OUT.mkdir(parents=True, exist_ok=True)
CACHE.mkdir(parents=True, exist_ok=True)
W, H = 1440, 900
BBOX = (113.12, 40.974, 113.29, 41.054)
GEO = json.loads((ROOT / 'data/map-v2/geographic-manifest.json').read_text())
COORDINATE = json.loads((ROOT / 'data/contracts/coordinate-contract.json').read_text())
assert COORDINATE['projected_crs'] == 'EPSG:32649'
assert COORDINATE['geographic_crs'] == 'EPSG:4326'
assert COORDINATE['origin_utm_egm2008_m'] == GEO['origin'], 'canonical origin differs'
assert COORDINATE['height_multiplier'] == 1
ZONES = json.loads((ROOT / 'data/map-v2/zones-and-assets.json').read_text())
ROUTES = json.loads((ROOT / 'data/map-v2/routes.json').read_text())['routes']
to_merc = Transformer.from_crs(COORDINATE['geographic_crs'], 3857, always_xy=True)
local_merc = Transformer.from_crs(COORDINATE['projected_crs'], 3857, always_xy=True)
west, south = to_merc.transform(*BBOX[:2])
east, north = to_merc.transform(*BBOX[2:])
transform = from_bounds(west, south, east, north, W, H)


def ll_pixel(lon, lat):
    x, y = to_merc.transform(lon, lat)
    return ((x-west)/(east-west)*W, (north-y)/(north-south)*H)


def local_pixel(p):
    x, y = local_merc.transform(p[0]+COORDINATE['origin_utm_egm2008_m'][0],
                                p[1]+COORDINATE['origin_utm_egm2008_m'][1])
    return ((x-west)/(east-west)*W, (north-y)/(north-south)*H)


def tile_pixel(lon, lat, z=12):
    return ((lon+180)/360*2**z*256,
            (1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*2**z*256)


ax, ay = tile_pixel(BBOX[0], BBOX[3])
bx, by = tile_pixel(BBOX[2], BBOX[1])
x0, x1 = int(ax//256), int(bx//256)
y0, y1 = int(ay//256), int(by//256)
tile_canvas = Image.new('RGB', ((x1-x0+1)*256, (y1-y0+1)*256), 'white')
urls = []
for x in range(x0, x1+1):
    for y in range(y0, y1+1):
        url = (f'https://tile.openstreetmap.org/12/{x}/{y}.png' if args.standard_provider == 'osm'
               else f'https://tile.openstreetmap.de/12/{x}/{y}.png')
        urls.append(url)
        cache = CACHE / f'12-{x}-{y}.png'
        if not cache.exists() and args.offline:
            continue
        if not cache.exists():
            req = Request(url, headers={'User-Agent': 'EnergyMapLocalPreview/0.2 (interactive design preview; cached)'})
            with urlopen(req, timeout=15) as response:
                cache.write_bytes(response.read())
        tile_canvas.paste(Image.open(cache).convert('RGB'), ((x-x0)*256, (y-y0)*256))
standard = tile_canvas.crop((round(ax-x0*256), round(ay-y0*256), round(bx-x0*256), round(by-y0*256))).resize((W,H),Image.Resampling.LANCZOS)
if args.offline:
    standard = Image.new('RGB', (W,H), '#f2f5f3')

source = np.array(Image.open(ROOT/'outputs/map-v2/satellite-utm49n.jpg').convert('RGB'))
sat = np.zeros((H,W,3), dtype=np.uint8)
src_transform = from_bounds(*GEO['utm_bounds'], source.shape[1], source.shape[0])
for channel in range(3):
    reproject(source[:,:,channel], sat[:,:,channel], src_transform=src_transform,
              src_crs='EPSG:32649', dst_transform=transform, dst_crs='EPSG:3857', resampling=Resampling.bilinear)
satellite = Image.fromarray(sat)

with rasterio.open(ROOT/'outputs/map-v2/terrain-utm49n.tif') as dem:
    elevation = np.zeros((H,W), dtype=np.float32)
    reproject(rasterio.band(dem,1), elevation, src_transform=dem.transform, src_crs=dem.crs,
              dst_transform=transform, dst_crs='EPSG:3857', resampling=Resampling.bilinear)
shade = np.clip(247 - (elevation-elevation.min())/max(1,np.ptp(elevation))*20, 220, 250).astype(np.uint8)
data_image = Image.fromarray(np.stack([shade,shade,shade],axis=2))
data_draw = ImageDraw.Draw(data_image)
contours = (elevation//10).astype(int)
edges = np.zeros((H,W), dtype=bool)
edges[1:,:] |= contours[1:,:] != contours[:-1,:]
edges[:,1:] |= contours[:,1:] != contours[:,:-1]
pixels = np.array(data_image)
pixels[edges] = (202,211,207)
data_image = Image.fromarray(pixels)
data_draw = ImageDraw.Draw(data_image)
for y in range(8,H,22):
    for x in range(8,W,22):
        data_draw.ellipse((x,y,x+2,y+2), fill='#ffffff')

font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 14)
small = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 11)
palette = ['#db9a29','#369d79','#9272c7','#578fc3']
facilities = {'DC_004':'DC-1','DC_005':'DC-2','DC_006':'DC-3','HUB_011':'CO2 HP','STORE_012':'PTES','DEMO_013':'R&D','AGRI_014':'A1','AGRI_015':'A2','AGRI_016':'B1','AGRI_017':'B2','AGRI_018':'C1','DRY_019':'C2'}
for name, image in [('standard',standard),('satellite',satellite),('data',data_image)]:
    image.convert('RGB').save(OUT/f'{name}-base.png')
    layer = Image.new('RGBA',(W,H))
    draw = ImageDraw.Draw(layer)
    for zone,color in zip(ZONES['zones'],palette):
        polygon = zone.get('source_geometry',{}).get('coordinates',[[]])[0]
        if polygon:
            pts=[ll_pixel(*p) for p in polygon]
            rgb=tuple(int(color[i:i+2],16) for i in (1,3,5))
            draw.polygon(pts,fill=(*rgb,28),outline=(*rgb,200),width=2)
    image=Image.alpha_composite(image.convert('RGBA'),layer)
    draw=ImageDraw.Draw(image)
    for route in ROUTES:
        if route['circuit'] not in ('user_water','source_water'):
            continue
        pts=[local_pixel(p) for p in route['sampled_xyz']]
        returned='RETURN' in route['route_id']
        color=('#a7e1ff' if returned else '#ffd1a5') if name=='satellite' else ('#377eab' if returned else '#d78c35')
        # Separate visual lanes only; never interpreted as physical offsets.
        pts=[(x+(3 if returned else -3),y) for x,y in pts]
        if route.get('dashed_future_candidate'):
            for i in range(0,len(pts)-1,3):
                draw.line(pts[i:i+2],fill=color,width=3)
        else:
            if name=='satellite':draw.line(pts,fill='#32463f',width=7)
            draw.line(pts,fill=color,width=3)
    for f in GEO['features']:
        if f['id'] not in facilities: continue
        x,y=local_pixel(f['xyz'])
        color='#282e35' if name!='satellite' else '#ffffff'
        draw.ellipse((x-6,y-6,x+6,y+6),fill=color,outline='#ffffff',width=2)
        label=facilities[f['id']]
        yy=y-28 if label not in ('A2','DC-3') else y+10
        xx=x+12
        tw=draw.textlength(label,font=font)+12
        draw.rounded_rectangle((xx,yy,xx+tw,yy+23),radius=3,fill='#ffffff',outline='#d0d5d2')
        draw.text((xx+6,yy+3),label,font=font,fill='#1e2b30')
    attribution={'standard':('Standard-map tiles unavailable: facility coordinates retained; retry or switch to satellite' if args.offline else '© OpenStreetMap contributors | Candidate facilities / schematic routes'),
                 'satellite':'EOxCloudless Sentinel-2 2024 · © EOX | Copernicus DEM GLO30 | Candidate scheme',
                 'data':'Copernicus DEM GLO30 | 10m contours · elevation only, no heat potential data'}[name]
    draw.rectangle((90,H-24,W-12,H),fill='#ffffff')
    if name == 'standard' and not args.offline and args.standard_provider == 'osmde':
        attribution = '© OpenStreetMap contributors · tiles: FOSSGIS openstreetmap.de | Candidate facilities / schematic routes'
    draw.text((98,H-20),attribution,font=small,fill='#4a5755')
    image.convert('RGB').save(OUT/f'{name}-design-map.png')

# Editable geographic marks for the next design revision. Same transform as backgrounds.
def simplify_pixels(points, tolerance=0.5):
    if len(points) < 3:
        return points
    a, b = np.array(points[0]), np.array(points[-1])
    span = b - a
    length = np.linalg.norm(span)
    distances = [np.linalg.norm(np.array(p)-a) if length == 0 else
                 abs(span[0]*(p[1]-a[1])-span[1]*(p[0]-a[0]))/length for p in points]
    index = int(np.argmax(distances))
    if distances[index] <= tolerance:
        return [points[0], points[-1]]
    return simplify_pixels(points[:index+1], tolerance)[:-1] + simplify_pixels(points[index:], tolerance)

for mode in ['standard', 'satellite', 'data']:
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    for zone, color in zip(ZONES['zones'], palette):
        polygon = zone.get('source_geometry', {}).get('coordinates', [[]])[0]
        if polygon:
            points = ' '.join(f'{x:.2f},{y:.2f}' for x,y in [ll_pixel(*p) for p in polygon])
            parts.append(f'<polygon points="{points}" fill="{color}" fill-opacity="0.10" stroke="{color}" stroke-width="1.5"/>')
    for route in ROUTES:
        if route['circuit'] not in ('user_water', 'source_water'):
            continue
        returned = 'RETURN' in route['route_id']
        coords = [(x + (3 if returned else -3), y) for x, y in [local_pixel(p) for p in route['sampled_xyz']]]
        points = ' '.join(f'{x:.2f},{y:.2f}' for x,y in simplify_pixels(coords))
        color = ('#a7e1ff' if returned else '#ffd1a5') if mode == 'satellite' else ('#377eab' if returned else '#d78c35')
        dash = 'stroke-dasharray="8 6"' if route.get('dashed_future_candidate') else ''
        if mode == 'satellite':
            parts.append(f'<polyline points="{points}" fill="none" stroke="#32463f" stroke-width="6" {dash}/>')
        parts.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="3.5" {dash}/>')
    marks = []
    for feature in GEO['features']:
        if feature['id'] not in facilities:
            continue
        x, y = local_pixel(feature['xyz'])
        parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="5" fill="#27343c" stroke="#ffffff" stroke-width="2"/>')
        marks.append({'object_id': feature['id'], 'label': facilities[feature['id']], 'x': x, 'y': y})
    parts.append('</svg>')
    (OUT/f'{mode}-overlay.svg').write_text(''.join(parts))
(OUT/'map-marks.json').write_text(json.dumps(marks, indent=2)+'\n')
artifact_names = [f'{mode}-{kind}.{suffix}' for mode in ['standard','satellite','data']
                  for kind,suffix in [('base','png'),('design-map','png'),('overlay','svg')]] + ['map-marks.json']
files={name:hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in artifact_names}
inputs=['data/map-v2/geographic-manifest.json','data/map-v2/zones-and-assets.json',
        'data/map-v2/routes.json','data/contracts/coordinate-contract.json',
        'outputs/map-v2/satellite-utm49n.jpg','outputs/map-v2/terrain-utm49n.tif']
metadata={'bbox_wgs84':BBOX,'crs':'EPSG:3857','osm_zoom':12,
          'standard_provider':args.standard_provider,'tile_urls':urls,
          'standard_tiles_status':'unavailable_design_error_state' if args.offline else 'loaded',
          'files':files,'facility_identity':'candidate_unverified',
          'data_layer':'DEM elevation, no inferred thermal potential',
          'purpose':'Figma design backgrounds; not registration or interactive product acceptance',
          'input_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in inputs},
          'transform':{'recipe':'local UTM grid -> EPSG:3857 image pixels; no 3D registration',
                       'origin_utm_egm2008_m':COORDINATE['origin_utm_egm2008_m'],
                       'blender_to_glb_matrix_row_major':COORDINATE['blender_to_glb_matrix_row_major'],
                       'vertical_reference':COORDINATE['vertical_reference'],
                       'independent_registration_status':COORDINATE['independent_registration_status']}}
(OUT/'map-design-sources.json').write_text(json.dumps(metadata,indent=2)+'\n')
print(json.dumps({'files':files,'tiles_cached':len(urls),'contract_verified':True}))
