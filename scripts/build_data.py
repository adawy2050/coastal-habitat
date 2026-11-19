"""Build a static habitat-pixel atlas from the corrected manuscript inputs.

No basin-wide pixels or manuscript files are published. Run with Python 3.12.
"""
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
from urllib.request import urlopen

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import xarray as xr

SITE = Path(__file__).resolve().parents[1]
ROOT = SITE.parent
DERIVED = ROOT / 'redsea_ghrsst_habitat/data/derived'
CORRECTED = ROOT / 'revision_round1/03_analyses/corrected_summaries'
OUT = SITE / 'dist/data'
CACHE = SITE / '_cache'
METRICS = ['mhw_days', 'mhw_frequency', 'mhw_mean_duration', 'mhw_mean_intensity', 'mhw_max_intensity', 'mhw_cumulative_intensity']
MODES = ['Nino34', 'IOD', 'NAO', 'AO', 'EAWR', 'NAtl_SSTA', 'PDO']
REGIONS = ['Northern and Central Red Sea', 'Southern Red Sea', 'Gulf of Aden']
HABITATS = ['coral', 'seagrass', 'mangrove']


def dump(path, obj):
    path.write_text(json.dumps(obj, separators=(',', ':'), allow_nan=False), encoding='utf-8')


def rounded(a, digits=4):
    a = np.round(np.asarray(a, dtype=float), digits).astype(object)
    a[~np.isfinite(np.asarray(a, dtype=float))] = None
    return a.tolist()


def download(url, path):
    if not path.exists():
        print('Downloading', path.name, flush=True)
        with urlopen(url, timeout=60) as response:
            data = response.read()
        path.write_bytes(data)


def prepare_assets():
    vendor = SITE / 'dist/vendor'
    vendor.mkdir(parents=True, exist_ok=True)
    for url, filename in [
        ('https://unpkg.com/leaflet@1.9.4/dist/leaflet.js', 'leaflet.js'),
        ('https://unpkg.com/leaflet@1.9.4/dist/leaflet.css', 'leaflet.css'),
        ('https://unpkg.com/leaflet@1.9.4/LICENSE', 'LEAFLET-LICENSE.txt'),
        ('https://cdn.plot.ly/plotly-2.35.2.min.js', 'plotly.min.js'),
        ('https://raw.githubusercontent.com/plotly/plotly.js/v2.35.2/LICENSE', 'PLOTLY-LICENSE.txt'),
    ]:
        download(url, vendor / filename)
    # A local vector coastline keeps this atlas independent of tile services.
    coast = CACHE / 'ne_50m_land.geojson'
    download('https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_land.geojson', coast)
    from shapely.geometry import shape, mapping
    features = []
    for feature in json.loads(coast.read_text(encoding='utf-8'))['features']:
        geom = shape(feature['geometry'])
        simplified = geom.simplify(.006, preserve_topology=True)
        features.append({'type': 'Feature', 'properties': {}, 'geometry': mapping(simplified)})
    dump(OUT / 'land.geojson', {'type': 'FeatureCollection', 'features': features})


def mur_metrics(cells):
    path = CACHE / 'mur_native_metrics.npz'
    if path.exists():
        cache = np.load(path)
        assert np.array_equal(cache['cells'], cells)
        return {m: cache[m] for m in METRICS}
    module_path = ROOT / 'revision_round1/tools/habitat_overlay_corrected.py'
    spec = importlib.util.spec_from_file_location('corrected_overlay', module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    parts = []
    pf = pq.ParquetFile(DERIVED / 'ghrsst_summary/ghrsst_mhw_events_analysis_domain.parquet')
    columns = ['lat_idx', 'lon_idx', 'start_date', 'end_date', 'start_doy', 'end_doy',
               'duration_days', 'cumulative_intensity_c', 'max_intensity_c']
    for k, batch in enumerate(pf.iter_batches(columns=columns, batch_size=1_000_000)):
        b = batch.to_pandas()
        cell = b.lat_idx.to_numpy(np.int64) * 2151 + b.lon_idx.to_numpy(np.int64)
        keep = np.isin(cell, cells)
        if keep.any():
            b = b.loc[keep].copy()
            b['cell'] = cell[keep]
            parts.append(b)
        if k % 8 == 0:
            print(f'MUR event catalogue: batch {k+1}, habitat cells only', flush=True)
    events = pd.concat(parts, ignore_index=True)
    print(f'Reconstructing annual metrics from {len(events):,} habitat-source-cell events', flush=True)
    years = np.arange(2003, 2026)
    full = module.complete_grid(module.annual_from_events(events, years), cells, years)
    arrays = {m: full[m].to_numpy().reshape(len(cells), len(years)).T.astype('<f4') for m in METRICS}
    np.savez_compressed(path, cells=cells, **arrays)
    return arrays


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(exist_ok=True)
    rec = pd.read_parquet(CORRECTED / 'habitat_record_attachment.parquet')
    rec = rec[rec.retained & rec.meow_ecoregion.isin(REGIONS)].copy()
    points = rec.drop_duplicates('grid_site_id').sort_values(['lat_idx', 'lon_idx']).reset_index(drop=True)
    mask = rec.assign(bit=rec.habitat_group.map({'coral': 1, 'seagrass': 2, 'mangrove': 4})).groupby('grid_site_id').bit.sum()
    mur = np.sort(rec.mur_cell.unique())
    oisst = np.sort((rec.oisst_i * 86 + rec.oisst_j).unique())
    mur_map = np.searchsorted(mur, points.mur_cell.to_numpy())
    oisst_map = np.searchsorted(oisst, (points.oisst_i * 86 + points.oisst_j).to_numpy())
    dump(OUT / 'pixels.json', {
        'columns': ['lon', 'lat', 'habitats', 'region', 'mur', 'oisst', 'murDistanceKm', 'oisstDistanceKm', 'latIndex', 'lonIndex'],
        'rows': [[round(float(p.lon), 2), round(float(p.lat), 2), int(mask[p.grid_site_id]), REGIONS.index(p.meow_ecoregion),
                  int(mur_map[i]), int(oisst_map[i]), round(float(p.mur_dist_km), 3), round(float(p.oisst_dist_km), 3),
                  int(p.lat_idx), int(p.lon_idx)] for i, p in points.iterrows()],
    })
    arrays = mur_metrics(mur)
    with xr.open_dataset(DERIVED / 'oisst/oisst_mhw_annual_metrics.nc') as ds:
        oarrays = {m: ds[m].to_numpy()[:, oisst // 86, oisst % 86].astype('<f4') for m in METRICS}
        olat, olon = ds.lat.to_numpy(), ds.lon.to_numpy()
    products = {
        'mur': {'name': 'GHRSST MUR', 'years': list(range(2003, 2026)), 'resolution': '0.01°', 'baseline': '2003–2022',
                'cells': [[round(float(31 + c % 2151 * .01), 2), round(float(9.5 + c // 2151 * .01), 2)] for c in mur]},
        'oisst': {'name': 'OISST', 'years': list(range(1982, 2026)), 'resolution': '0.25°', 'baseline': '1982–2011',
                  'cells': [[float(olon[c % 86]), float(olat[c // 86])] for c in oisst]},
    }
    checks = []
    for product, values, native in [('mur', arrays, mur), ('oisst', oarrays, oisst)]:
        suffix = '' if product == 'mur' else '_oisst'
        ref = pd.read_csv(CORRECTED / f'habitat_meow_year_summary{suffix}.csv')
        rec_cells = rec.mur_cell.to_numpy() if product == 'mur' else (rec.oisst_i * 86 + rec.oisst_j).to_numpy()
        positions = np.searchsorted(native, rec_cells)
        for m, a in values.items():
            # Validate full-precision native arrays before writing browser assets.
            for (h, region), sub in rec.groupby(['habitat_group', 'meow_ecoregion']):
                take = (rec.habitat_group.to_numpy() == h) & (rec.meow_ecoregion.to_numpy() == region)
                sampled = a[:, positions[take]]
                means = np.nanmean(sampled.astype(float), axis=1)
                r = ref[(ref.habitat_group == h) & (ref.meow_ecoregion == region)].sort_values('year')
                diff = float(np.nanmax(np.abs(means - r[m].to_numpy())))
                checks.append({'product': product, 'metric': m, 'habitat': h, 'region': region, 'maxAbsDifference': diff})
                assert diff < 0.00015, (product, m, h, region, diff)
            a.astype('<f4').tofile(OUT / f'{product}_{m}.f32')
        assert np.all((values['mhw_days'] >= 0) & (values['mhw_days'] <= 365))
        print(product, len(native), 'native SST cells, annual metrics verified', flush=True)
    # Annual mean SST is sampled only at the 325 OISST cells attached to habitats.
    sst_cache = CACHE / 'oisst_annual_sst.npy'
    if sst_cache.exists():
        sst = np.load(sst_cache)
    else:
        rows = []
        for year in range(1982, 2026):
            with xr.open_dataset(ROOT / f'redsea_ghrsst_habitat/data/raw/oisst_yearly/oisst_v2_1_redsea_{year}.nc') as ds:
                a = ds.sst.to_numpy()[:, oisst // 86, oisst % 86]
                rows.append(np.nanmean(a, axis=0))
            if year % 10 == 0:
                print('Sampling habitat-pixel annual SST', year, flush=True)
        sst = np.asarray(rows, dtype='<f4')
        assert np.isfinite(sst).all() and (sst > 10).all() and (sst < 40).all()
        np.save(sst_cache, sst)
    sst.astype('<f4').tofile(OUT / 'oisst_sst.f32')
    monthly_path = ROOT / 'revision_round1/03_analyses/extended_climate_indices/monthly_original_plus_extra.csv'
    monthly = pd.read_csv(monthly_path).query('1980 <= year <= 2025').sort_values(['year', 'month'])
    assert monthly.loc[monthly.year >= 1982, MODES].notna().all().all()
    annual = monthly.groupby('year')[MODES].mean()
    dump(OUT / 'climate.json', {'modes': MODES, 'monthly': {'dates': [f'{r.year:04.0f}-{r.month:02.0f}-15' for r in monthly.itertuples()],
          'values': {m: rounded(monthly[m], 6) for m in MODES}}, 'annual': {'years': annual.index.tolist(),
          'values': {m: rounded(annual[m], 6) for m in MODES}}})
    dump(OUT / 'metadata.json', {'version': '2026-10-18', 'regions': REGIONS, 'habitats': HABITATS,
          'pixels': len(points), 'habitatRecords': len(rec), 'metrics': METRICS, 'products': products,
          'arrayFormat': 'little-endian float32; year-major, then native source cell; NaN means no events for intensity/duration',
          'source': 'Corrected manuscript habitat attachments and saved event catalogue; no new SST detection run',
          'climateOrder': MODES, 'annualSstProduct': 'OISST v2.1'})
    dump(OUT / 'validation.json', {'checks': checks, 'pixelCount': len(points), 'recordCount': len(rec),
          'allChecksPassed': True, 'maxSummaryDifference': max(x['maxAbsDifference'] for x in checks)})
    prepare_assets()
    assets = {str(p.relative_to(SITE / 'dist')).replace('\\', '/'): {'bytes': p.stat().st_size,
             'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in OUT.iterdir() if p.is_file() and p.name != 'manifest.json'}
    dump(OUT / 'manifest.json', {'files': assets, 'inputHashes': {str(p.relative_to(ROOT)).replace('\\', '/'):
          hashlib.sha256(p.read_bytes()).hexdigest() for p in [CORRECTED / 'habitat_record_attachment.parquet', monthly_path]}})
    print('DATA READY:', len(points), 'habitat pixels;', round(sum(p.stat().st_size for p in (SITE / 'dist').rglob('*') if p.is_file()) / 1e6, 1), 'MB', flush=True)


if __name__ == '__main__':
    main()
