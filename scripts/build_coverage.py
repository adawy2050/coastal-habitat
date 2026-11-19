"""Render the study's habitat inventory as transparent publication map tiles.

Only rendered images are exported; original GIS geometries/attributes stay local.
"""
from pathlib import Path
import json
import geopandas as gpd
import pandas as pd
import numpy as np
from PIL import Image
from rasterio.features import rasterize
from rasterio.transform import from_bounds

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT.parent/'redsea_ghrsst_habitat/data/derived/habitat_layers_redsea.gpkg'
OUT=ROOT/'dist/coverage'
COLORS={'coral':(255,178,58),'seagrass':(62,213,218),'mangrove':(194,125,255)}
ORIGIN=20037508.342789244


def main():
    frames=[gpd.read_file(SOURCE).to_crs(3857)]
    gulf=ROOT.parent/'arabian_gulf_ghrsst_habitat/data/derived/habitat_layers_arabian_persian_gulf.gpkg'
    if gulf.exists():frames.append(gpd.read_file(gulf).to_crs(3857))
    frame=gpd.GeoDataFrame(pd.concat(frames,ignore_index=True),crs=3857)
    index={'maxNativeZoom':12,'minZoom':4,'colors':{h:'#%02x%02x%02x'%rgb for h,rgb in COLORS.items()},
        'source':'UNEP-WCMC study inventories: coral 2021, seagrass 2021, mangroves 2010',
        'attributionUrl':'https://www.unep-wcmc.org/','format':'Rendered publication map only; original polygons are not distributed',
        'tiles':{}}
    for habitat,rgb in COLORS.items():
        sub=frame[frame.habitat_group==habitat].reset_index(drop=True)
        spatial=sub.sindex
        keys=[]
        for z in range(4,13):
            width=ORIGIN*2/(2**z)
            candidates=set()
            for geom in sub.geometry:
                # Separate distant components to avoid mostly empty bounding boxes.
                pieces=list(geom.geoms) if geom.geom_type=='MultiPolygon' else [geom]
                for piece in pieces:
                    xmin,ymin,xmax,ymax=piece.bounds
                    for x in range(int(np.floor((xmin+ORIGIN)/width)),int(np.floor((xmax+ORIGIN)/width))+1):
                        for y in range(int(np.floor((ORIGIN-ymax)/width)),int(np.floor((ORIGIN-ymin)/width))+1):
                            candidates.add((x,y))
            for x,y in sorted(candidates):
                xmin=-ORIGIN+x*width;xmax=xmin+width;ymax=ORIGIN-y*width;ymin=ymax-width
                ids=list(spatial.intersection((xmin,ymin,xmax,ymax)))
                if not ids:continue
                mask=rasterize([(g,1) for g in sub.geometry.iloc[ids]],out_shape=(256,256),
                    transform=from_bounds(xmin,ymin,xmax,ymax,256,256),fill=0,all_touched=True,dtype='uint8')
                if not mask.any():continue
                rgba=np.zeros((256,256,4),dtype=np.uint8);rgba[:,:,:3]=rgb;rgba[:,:,3]=mask*170
                path=OUT/habitat/str(z)/str(x)/f'{y}.png';path.parent.mkdir(parents=True,exist_ok=True)
                Image.fromarray(rgba).save(path,optimize=True)
                keys.append(f'{z}/{x}/{y}')
            print(habitat,'zoom',z,'total rendered tiles',len(keys),flush=True)
        index['tiles'][habitat]=keys
    OUT.mkdir(exist_ok=True)
    (OUT/'index.json').write_text(json.dumps(index,separators=(',',':')),encoding='utf-8')
    print('COVERAGE READY',sum(len(v) for v in index['tiles'].values()),'tiles',flush=True)


if __name__=='__main__':main()
