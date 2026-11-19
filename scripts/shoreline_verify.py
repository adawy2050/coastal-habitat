"""Check display-only GSHHG tile assets and their recorded provenance."""
import hashlib
import json
from pathlib import Path

from shapely.geometry import shape

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'dist' / 'coastline'
index = json.loads((BASE / 'index.json').read_text(encoding='utf-8'))
assert index['simplificationTolerance'] == 0
assert index['license'] == 'LGPL-3.0-or-later'
assert index['sourceArchiveSha256'] == '8dbbe7e071e77e9e75f2d639239099ebca8d5c16d6a07df8169729d49f15cf41'
assert (BASE / 'COPYING.LESSERv3').stat().st_size > 7000
counts = {'land': 0, 'water': 0, 'coast': 0}
invalid = []
for tile in index['tiles']:
    path = BASE / tile['path']
    raw = path.read_bytes()
    assert len(raw) == tile['bytes']
    assert hashlib.sha256(raw).hexdigest() == tile['sha256']
    data = json.loads(raw)
    assert len(data['features']) == tile['features']
    west, south, east, north = tile['bounds']
    for feature in data['features']:
        props = feature['properties']
        assert props['kind'] in counts
        assert props['level'] in range(1, 5)
        geom = shape(feature['geometry'])
        assert not geom.is_empty
        x0, y0, x1, y1 = geom.bounds
        assert x0 >= west - 1e-5 and x1 <= east + 1e-5
        assert y0 >= south - 1e-5 and y1 <= north + 1e-5
        if not geom.is_valid:
            invalid.append([tile['path'], props, str(geom.geom_type)])
        counts[props['kind']] += 1
overview = (BASE / index['overview']['path']).read_bytes()
assert hashlib.sha256(overview).hexdigest() == index['overview']['sha256']
assert len(overview) == index['overview']['bytes']
overview_data = json.loads(overview)
overview_geoms = [shape(f['geometry']) for f in overview_data['features']]
assert min(g.bounds[0] for g in overview_geoms) <= -179.9
assert max(g.bounds[2] for g in overview_geoms) >= 179.9
assert min(g.bounds[1] for g in overview_geoms) <= -89.9
assert all(g.is_valid for g in overview_geoms)
assert all(f['properties']['kind'] in ('land', 'water') for f in overview_data['features'])
assert sum(t['bytes'] for t in index['tiles']) == index['totalBytes']
result = {'tiles': len(index['tiles']), 'tileBytes': index['totalBytes'],
          'overviewBytes': len(overview), 'features': counts,
          'invalidAfterRounding': invalid,
          'sourceVersion': index['version']}
(ROOT / 'qa' / 'shoreline_verification.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result, indent=2))
assert not invalid, 'Coordinate rounding introduced invalid polygon geometry'
