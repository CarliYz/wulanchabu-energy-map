"""Prepare traceable UTM terrain and a separately licensed satellite texture."""
from pathlib import Path
import hashlib
import json
import struct

import numpy as np
from PIL import Image
from pyproj import Geod, Transformer
import rasterio
from rasterio.merge import merge
from rasterio.transform import from_bounds
from rasterio.warp import reproject, Resampling, transform_bounds


ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / 'work/map-v2/raw'
OUT = ROOT / 'outputs/map-v2'
OUT.mkdir(parents=True, exist_ok=True)
BBOX = (113.065, 40.935, 113.328, 41.0883)
CRS = 'EPSG:32649'
TRANSFORM = Transformer.from_crs(4326, CRS, always_xy=True)
ORIGIN = (*TRANSFORM.transform(113.2275, 40.9935), 1200.0)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    names = ['copernicus_N40_E113.tif', 'copernicus_N41_E113.tif']
    datasets = [rasterio.open(RAW / name) for name in names]
    # UTM's north-aligned rectangle extends outside the WGS84 rectangle at
    # its rotated corners. Read a real-data collar instead of filling holes.
    collar=(BBOX[0]-.02,BBOX[1]-.02,BBOX[2]+.02,BBOX[3]+.02)
    mosaic, source_transform = merge(datasets, bounds=collar)
    bounds = transform_bounds(4326, CRS, *BBOX, densify_pts=21)
    nx = int(np.ceil((bounds[2] - bounds[0]) / 40))
    ny = int(np.ceil((bounds[3] - bounds[1]) / 40))
    affine = from_bounds(*bounds, nx, ny)
    heights = np.full((ny, nx), -9999, dtype=np.float32)
    reproject(mosaic[0], heights, src_transform=source_transform,
              src_crs=datasets[0].crs, dst_transform=affine, dst_crs=CRS,
              src_nodata=datasets[0].nodata, dst_nodata=-9999,
              resampling=Resampling.bilinear)
    assert np.isfinite(heights).all() and np.all(heights > 0), 'Invalid DEM pixels'
    assert heights.max() - heights.min() > 5, 'Flat or invalid DEM'
    with rasterio.open(OUT / 'terrain-utm49n.tif', 'w', driver='GTiff',
                       height=ny, width=nx, count=1, dtype='float32', crs=CRS,
                       transform=affine, nodata=-9999, compress='deflate') as dst:
        dst.write(heights, 1)
    xx, yy = np.meshgrid(np.arange(nx), np.arange(ny))
    px = affine.c + (xx + .5) * affine.a
    py = affine.f + (yy + .5) * affine.e
    verts = np.stack([px - ORIGIN[0], py - ORIGIN[1], heights - ORIGIN[2]], axis=2).reshape(-1, 3).astype('<f4')
    # Binary PLY avoids executing file reads in Blender's MCP safe mode.
    with (OUT / 'terrain.ply').open('wb') as f:
        f.write(('ply\nformat binary_little_endian 1.0\nelement vertex %d\n'
                 'property float x\nproperty float y\nproperty float z\n'
                 'element face %d\nproperty list uchar int vertex_indices\nend_header\n'
                 % (len(verts), (nx-1)*(ny-1))).encode())
        f.write(verts.tobytes())
        for row in range(ny-1):
            for col in range(nx-1):
                a = row*nx+col
                f.write(struct.pack('<B4i',4,a,a+nx,a+nx+1,a+1))
    request = json.loads((ROOT / 'data/map-v2/imagery-request.json').read_text())
    original = np.asarray(Image.open(RAW / 'eox-sentinel2-2024.jpg').convert('RGB'))
    assert original.shape[:2] == (3170,4096), original.shape
    tw, th = 4096, round(4096*(bounds[3]-bounds[1])/(bounds[2]-bounds[0]))
    image_affine = from_bounds(*request['webmercator_bbox'], original.shape[1], original.shape[0])
    texture_affine = from_bounds(*bounds, tw, th)
    texture = np.zeros((th,tw,3),dtype=np.uint8)
    for band in range(3):
        reproject(original[:,:,band], texture[:,:,band], src_transform=image_affine,
                  src_crs='EPSG:3857',dst_transform=texture_affine,dst_crs=CRS,
                  resampling=Resampling.bilinear)
    Image.fromarray(texture).save(OUT / 'satellite-utm49n.jpg', quality=96)
    # Low resolution unmodified-source-derived preview for the source record.
    Image.fromarray(texture).resize((1200,round(th*1200/tw))).save(ROOT/'research/map-v2/satellite-utm-preview.jpg',quality=92)
    seed=json.loads((ROOT/'inputs/original/乌兰察布算热储_建模种子图层_待核.geojson').read_text())
    def point(lon,lat):
        x,y=TRANSFORM.transform(lon,lat)
        col,row=~affine*(x,y)
        row=int(np.clip(round(row-.5),0,ny-1)); col=int(np.clip(round(col-.5),0,nx-1))
        return [round(x-ORIGIN[0],4),round(y-ORIGIN[1],4),round(float(heights[row,col])-ORIGIN[2],4)]
    features=[]
    for feature in seed['features']:
        g=feature['geometry']; typ=g['type']; coords=g['coordinates']
        if typ=='Point': xyz=point(*coords)
        elif typ=='LineString': xyz=[point(*p) for p in coords]
        else: xyz=[[point(*p) for p in ring] for ring in coords]
        features.append({'id':feature['properties']['object_id'],'properties':feature['properties'],'type':typ,'xyz':xyz})
    geod=Geod(ellps='WGS84')
    controls=[]
    for lon,lat in [(113.2275,40.9935),(113.2045,41.016),(113.185,41.0335)]:
        x,y=TRANSFORM.transform(lon,lat)
        back=Transformer.from_crs(CRS,4326,always_xy=True).transform(x,y)
        err=geod.inv(lon,lat,*back)[2]
        controls.append({'lonlat':[lon,lat],'utm':[x,y],'roundtrip_error_m':err})
    manifest={'revision':'map-build-v2','crs':CRS,'origin':ORIGIN,'bbox_wgs84':BBOX,
              'utm_bounds':bounds,'terrain_grid':[nx,ny],'sample_spacing_m':[affine.a,-affine.e],
              'height_multiplier':1.0,'height_range_m':[float(heights.min()),float(heights.max())],
              'valid_pixel_count':int(heights.size),'nodata_pixel_count':int((heights==-9999).sum()),
              'vertical_reference':'Copernicus DEM EGM2008 orthometric heights; not engineering ground survey',
              'position_status':'source seed geometry remains unverified; projection roundtrip is not field validation',
              'controls':controls,'texture_request':request,
              'dem_sources':[{'file':name,'sha256':digest(RAW/name),'crs':str(ds.crs),'transform':list(ds.transform),'nodata':ds.nodata,'tags':ds.tags()} for name,ds in zip(names,datasets)],
              'features':features}
    (ROOT/'data/map-v2/geographic-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    # Literal data is injected into safe-mode scripts, with no eval/open in Blender.
    (ROOT/'work/map-v2/geo_literal.py').write_text('GEO = '+repr(manifest)+'\n')
    print(json.dumps({'outcome':'pass','grid':[nx,ny],'elevation_m':manifest['height_range_m'],'control_max_error_m':max(c['roundtrip_error_m'] for c in controls),'features':len(features)}))


if __name__=='__main__':
    main()
