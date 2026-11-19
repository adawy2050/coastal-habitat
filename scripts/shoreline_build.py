"""Build clipped, unsimplified GSHHG display tiles; never changes analysis masks."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
import zipfile

import geopandas as gpd
import requests
import shapely
from shapely.geometry import box, mapping

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / '_cache' / 'gshhg'
OUT = ROOT / 'dist' / 'coastline'
URL = 'https://github.com/GenericMappingTools/gshhg-gmt/releases/download/2.3.7/gshhg-shp-2.3.7.zip'
SOURCE_SHA256 = '8dbbe7e071e77e9e75f2d639239099ebca8d5c16d6a07df8169729d49f15cf41'
AREAS = {'redsea': [29, 8, 54, 33], 'gulf': [47, 21, 61, 33], 'eastasia': [109, -1, 161, 56]}
SIZE = 4


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rounded(value):
    if isinstance(value, dict):
        return {k: rounded(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [rounded(v) for v in value]
    if isinstance(value, float):
        return round(value, 5)
    return value


def geometry_parts(geom, polygons):
    if geom is None or geom.is_empty:
        return []
    if geom.geom_type in (('Polygon', 'MultiPolygon') if polygons else ('LineString', 'MultiLineString')):
        return [geom]
    if hasattr(geom, 'geoms'):
        return [p for g in geom.geoms for p in geometry_parts(g, polygons)]
    return []


def main():
    archive = ROOT / '_cache' / 'gshhg-shp-2.3.7.zip'
    archive.parent.mkdir(exist_ok=True)
    if not archive.exists():
        response = requests.get(URL, stream=True, timeout=120)
        response.raise_for_status()
        with archive.open('wb') as handle:
            for chunk in response.iter_content(1024 * 1024):
                handle.write(chunk)
    if digest(archive) != SOURCE_SHA256:
        raise RuntimeError('GSHHG source archive hash does not match the audited release')
    CACHE.mkdir(exist_ok=True)
    OUT.mkdir(exist_ok=True)
    (OUT / 'tiles').mkdir(exist_ok=True)
    with zipfile.ZipFile(archive) as zipped:
        for name in ('LICENSE.TXT', 'COPYING.LESSERv3', 'README.TXT', 'SHAPEFILES.TXT'):
            (OUT / name).write_bytes(zipped.read(name))
        for level in range(1, 6):
            for ext in ('shp', 'shx', 'dbf', 'prj'):
                name = f'GSHHS_shp/f/GSHHS_f_L{level}.{ext}'
                if not (CACHE / name).exists():
                    zipped.extract(name, CACHE)
    gpl = OUT / 'COPYINGv3'
    if not gpl.exists():
        response = requests.get('https://raw.githubusercontent.com/gcc-mirror/gcc/master/COPYING3', timeout=60)
        response.raise_for_status()
        if hashlib.sha256(response.content).hexdigest() != '8ceb4b9ee5adedde47b31e975c1d90c73ad27b6b165a1dcd80c7c545eb65b903':
            raise RuntimeError('GPL license text hash changed')
        gpl.write_bytes(response.content)

    combined = shapely.union_all([box(*b) for b in AREAS.values()])
    levels = {}
    for level in range(1, 5):
        frame = gpd.read_file(CACHE / f'GSHHS_shp/f/GSHHS_f_L{level}.shp', bbox=combined.bounds)
        frame = frame[frame.intersects(combined)].copy()
        levels[level] = frame
        print(f'Loaded L{level}: {len(frame):,} polygons', flush=True)

    overview = []
    for level in range(1, 6):
        # Antarctica ice-front polygons are L5 in the source, drawn as land.
        draw_level = 1 if level == 5 else level
        frame = gpd.read_file(CACHE / f'GSHHS_shp/f/GSHHS_f_L{level}.shp', where='area >= 5')
        # Islands below 5 km² cannot be resolved at the overview scale. All are
        # retained without simplification in the detailed tiles at zoom 8+.
        for geom in frame.geometry:
            if not geom.is_valid:
                geom = shapely.make_valid(geom)
            geom = geom.simplify(.03, preserve_topology=True)
            for part in geometry_parts(geom, True):
                overview.append({'type': 'Feature', 'properties': {
                    'kind': 'land' if draw_level % 2 else 'water', 'level': draw_level,
                    'sourceLevel': level},
                    'geometry': rounded(mapping(part))})
    overview_path = OUT / 'overview.geojson'
    overview_path.write_text(json.dumps({'type': 'FeatureCollection', 'features': overview},
                                       separators=(',', ':')), encoding='utf-8', newline='\n')
    overview_info = {'path': 'overview.geojson', 'simplificationToleranceDegrees': .03,
                     'coverage': 'global, unclipped',
                     'rendering': 'Unclipped overview polygons can use stroke:true to draw coastlines; no duplicate kind=coast features are included in the overview.',
                     'minimumSourcePolygonAreaKm2': 5,
                     'bytes': overview_path.stat().st_size, 'sha256': digest(overview_path)}
    if '--overview-only' in sys.argv:
        index_path = OUT / 'index.json'
        index = json.loads(index_path.read_text(encoding='utf-8'))
        index['overview'] = overview_info
        index_path.write_text(json.dumps(index, indent=2), encoding='utf-8', newline='\n')
        print(f'Overview rebuilt: {overview_path.stat().st_size / 1024**2:.2f} MiB', flush=True)
        return

    tiles = []
    total_vertices = 0
    for west in range(28, 164, SIZE):
        for south in range(-4, 56, SIZE):
            bounds = [west, south, west + SIZE, south + SIZE]
            tile_box = box(*bounds)
            if not tile_box.intersects(combined):
                continue
            clip = tile_box.intersection(combined)
            if clip.area == 0:
                continue
            features = []
            for level, frame in levels.items():
                candidates = frame.iloc[frame.sindex.query(clip, predicate='intersects')]
                for geom in candidates.geometry:
                    if not geom.is_valid:
                        geom = shapely.make_valid(geom)
                    land = geom.intersection(clip)
                    for part in geometry_parts(land, True):
                        total_vertices += shapely.get_num_coordinates(part)
                        features.append({'type': 'Feature', 'properties': {
                            'kind': 'land' if level % 2 else 'water', 'level': level},
                            'geometry': rounded(mapping(part))})
                    # Clip original boundaries independently: no artificial tile-frame outlines.
                    coast = geom.boundary.intersection(clip)
                    for part in geometry_parts(coast, False):
                        features.append({'type': 'Feature', 'properties': {'kind': 'coast', 'level': level},
                                         'geometry': rounded(mapping(part))})
            if not features:
                continue
            path = OUT / 'tiles' / f'{west}_{south}.geojson'
            path.write_text(json.dumps({'type': 'FeatureCollection', 'features': features},
                                       separators=(',', ':')), encoding='utf-8', newline='\n')
            tiles.append({'path': f'tiles/{path.name}', 'bounds': bounds, 'bytes': path.stat().st_size,
                          'sha256': digest(path), 'features': len(features)})
            print(f'{path.name}: {path.stat().st_size / 1e3:.0f} kB', flush=True)

    index = {
        'version': 'gshhg-2.3.7-full-20261022',
        'source': 'GSHHG 2.3.7, full-resolution (f), levels 1–4',
        'sourceUrl': 'https://github.com/GenericMappingTools/gshhg-gmt/releases/tag/2.3.7',
        'downloadUrl': URL,
        'sourceArchiveSha256': SOURCE_SHA256,
        'authors': 'Paul Wessel and Walter H. F. Smith',
        'citation': 'Wessel and Smith (1996), doi:10.1029/96JB00104',
        'license': 'LGPL-3.0-or-later',
        'licenseFile': 'COPYING.LESSERv3',
        'attributionHtml': 'Shoreline: <a href="https://www.soest.hawaii.edu/wessel/gshhg/">GSHHG 2.3.7</a>, Wessel &amp; Smith (LGPL)',
        'crs': 'EPSG:4326',
        'coordinateDecimalPlaces': 5,
        'simplificationTolerance': 0,
        'tileSizeDegrees': SIZE,
        'recommendedMinZoom': 8,
        'maxZoom': 18,
        'overview': overview_info,
        'areas': AREAS,
        'note': 'Original full-resolution vertices retained, clipped and rounded to five decimal degrees for display. GSHHG is based on historical source surveys; detail does not imply current shoreline accuracy or metre-scale positional accuracy. Display only; habitat and heatwave analysis grids are unchanged.',
        'drawOrder': ['L1 land', 'L2 water', 'L3 land', 'L4 water', 'coast'],
        'rendering': 'Fill polygons without stroke; draw kind=coast separately. Coast features use original boundaries, so tile clipping edges are not drawn as shorelines. Cache tiles and load only those intersecting the current view.',
        'polygonVertices': int(total_vertices),
        'totalBytes': sum(t['bytes'] for t in tiles),
        'tiles': tiles,
    }
    (OUT / 'index.json').write_text(json.dumps(index, indent=2), encoding='utf-8', newline='\n')
    print(f'Finished {len(tiles)} tiles, {index["totalBytes"] / 1024**2:.2f} MiB', flush=True)


if __name__ == '__main__':
    main()
