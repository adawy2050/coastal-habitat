"""Verify additional display records against unchanged annual study arrays."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]/'dist'
meta=json.loads((ROOT/'data/metadata.json').read_text())
for basin,(start,end) in meta['products']['oisst']['basinCellRanges'].items():
    base=ROOT/'detail/daily'/basin
    index=json.loads((base/'index.json').read_text())
    dates=pd.to_datetime(index['dates'])
    assert len(dates)==16071 and dates.is_unique and dates.is_monotonic_increasing
    values=[]
    for record in index['files']:
        content=(base/record['file']).read_bytes()
        assert len(content)==record['bytes'] and hashlib.sha256(content).hexdigest()==record['sha256']
        a=np.frombuffer(content,dtype='<i2').astype(float)
        a[a==-32768]=np.nan
        values.append(a*.01)
    a=np.array(values).T
    annual=np.fromfile(ROOT/'data/oisst_sst.f32',dtype='<f4').reshape(44,-1)[:,start:end]
    means=np.array([np.nanmean(a[dates.year==y],axis=0) for y in range(1982,2026)])
    assert np.max(abs(means-annual))<.0001
    print(basin,len(values),'daily source records reproduce annual SST means')
index=json.loads((ROOT/'detail/monthly/index.json').read_text())
for product,p in index['products'].items():
    blocks=[]
    for name in p['files']:
        blocks.append(np.fromfile(ROOT/'detail/monthly'/name,dtype='uint8').reshape(-1,len(p['dates'])))
    a=np.concatenate(blocks).T.reshape(len(meta['products'][product]['years']),12,p['cells'])
    annual=np.fromfile(ROOT/f'data/{product}_mhw_days.f32',dtype='<f4').reshape(a.shape[0],p['cells'])
    assert np.array_equal(a.sum(axis=1),annual)
    print(product,'monthly counts reproduce every annual source-cell MHW total')
daily=json.loads((ROOT/'detail/climate_daily.json').read_text())
for mode,record in daily['modes'].items():
    assert len(record['dates'])==len(record['values'])>10000
    assert record['dates']==sorted(set(record['dates'])) and all(abs(v)<90 for v in record['values'])
    assert record['source'].startswith('https://ftp.cpc.ncep.noaa.gov/')
print('PASS: daily SST, exact monthly MHW totals, daily climate dates and source metadata.')
