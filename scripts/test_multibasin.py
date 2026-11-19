"""Independently validate Gulf source values and preservation of the Red Sea."""
from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'dist/data'
BASE=ROOT/'_cache/redsea_atlas_base';GULF=ROOT/'_cache/gulf_extracted'
meta=json.loads((DATA/'metadata.json').read_text());old=json.loads((BASE/'metadata.json').read_text())
points=np.array(json.loads((DATA/'pixels.json').read_text())['rows'])
local=json.loads((GULF/'pixels.json').read_text())['rows']
assert meta['pixels']>=65348 and meta['habitatRecords']>=74402
assert sum(b['pixels'] for b in meta['basins'] if b['id'] in ['redsea','gulf'])==65348
assert len({(p[0],p[1]) for p in points})==len(points)
outlook=json.loads((DATA/'outlook.json').read_text())
checked=0
for key,suffix in [('mur','ghrsst'),('oisst','oisst')]:
    n=len(meta['products'][key]['cells']);nr=len(old['products'][key]['cells']);years=meta['products'][key]['years']
    source=pd.read_parquet(ROOT/'_cache/gulf_source'/f'site_annual_mhw_{suffix}.parquet').drop_duplicates(['grid_site_id','year'])
    coords=np.array(meta['products'][key]['cells'])
    native=points[old['pixels']:,4 if key=='mur' else 5].astype(int)
    ids=[f'ghrsst_{int(p[8]):05d}_{int(p[9]):05d}' for p in local]
    native_by_id=dict(zip(ids,native))
    source=source[source.grid_site_id.isin(ids)].copy()
    index=source.grid_site_id.map(native_by_id).to_numpy()
    original_xy=source[['lon','lat']].to_numpy() if key=='mur' else source[['oisst_lon','oisst_lat']].to_numpy()
    matched=np.max(abs(coords[index]-original_xy),axis=1)<1e-5
    source=source.loc[matched];index=index[matched]
    yi=np.searchsorted(years,source.year.to_numpy())
    assert len(source)>10000
    for metric in meta['metrics']:
        a=np.fromfile(DATA/f'{key}_{metric}.f32',dtype='<f4').reshape(len(years),n)
        previous=np.fromfile(BASE/f'{key}_{metric}.f32',dtype='<f4').reshape(len(years),nr)
        assert np.array_equal(a[:,:nr],previous,equal_nan=True)
        assert np.allclose(a[yi,index],source[metric].to_numpy(),atol=1e-5,rtol=0,equal_nan=True),(key,metric)
        checked+=len(source)
    for path in BASE.glob(f'{key}_outlook_*.f32'):
        previous=np.fromfile(path,dtype='<f4');a=np.fromfile(DATA/path.name,dtype='<f4')
        if 'coefficients' in path.name:a=a.reshape(n,7)[:nr].ravel()
        elif 'backtest' in path.name:a=a.reshape(-1,n)[:,:nr].ravel()
        else:a=a[:nr]
        assert np.array_equal(a,previous,equal_nan=True),path.name
    ntest=len(outlook['pixelOutlooks'][key]['testYears'])
    assert np.fromfile(DATA/f'{key}_outlook_backtest_predictions.f32',dtype='<f4').size==ntest*n
gulf_groups=[g for g in json.loads((DATA/'seasonal_groups.json').read_text())['groups'] if g['basin']=='gulf']
assert len(gulf_groups)==8 and not any(g['region']=='Gulf of Oman' and g['habitat']=='seagrass' for g in gulf_groups)
audit=json.loads((DATA/'gulf_validation.json').read_text())
assert audit['sourceCompleteness']['murDailyHeadersReadable']
assert audit['sourceCompleteness']['murDailyFiles']==8401
assert audit['attachmentAudit']['excludedBeyond5km']==56
(ROOT/'qa/multibasin_data_results.json').write_text(json.dumps({'passed':True,'sourceMetricComparisons':checked,'redSeaAnnualAndForecastValuesUnchanged':True,'gulfPixels':len(local),'combinedPixels':len(points)},indent=2))
print(f'PASS: {checked:,} Gulf annual source-value comparisons; Red Sea histories, coefficients, backtests and probabilities unchanged; actual habitat groups only.')
