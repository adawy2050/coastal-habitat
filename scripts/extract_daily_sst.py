"""Extract display-only daily OISST values at existing native habitat sources.

No detection, model fitting or modifications to the source files. Temperatures
are stored as signed little-endian int16 hundredths of a degree (raw OISST
precision), with -32768 for missing data. Dates retain real Gregorian leap days.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import xarray as xr


def extract(source, cells, output, pattern):
    output.mkdir(parents=True, exist_ok=True)
    frames=[];dates=[]
    for year in range(1982, 2026):
        path=source/pattern.format(year=year)
        with xr.open_dataset(path) as ds:
            lat=np.asarray(ds.lat);lon=np.asarray(ds.lon)
            iy=np.array([np.argmin(abs(lat-c[1])) for c in cells])
            ix=np.array([np.argmin(abs(lon-c[0])) for c in cells])
            assert max(abs(lat[iy]-np.array(cells)[:,1]))<.002
            assert max(abs(lon[ix]-np.array(cells)[:,0]))<.002
            values=ds.sst.values[:,iy,ix]
            if float(np.nanmedian(values))>100:values=values-273.15
            encoded=np.where(np.isfinite(values),np.rint(values*100),-32768).astype('<i2')
            frames.append(encoded);dates.extend(pd.to_datetime(ds.time.values).strftime('%Y-%m-%d'))
        if year%10==0:print(year,flush=True)
    a=np.concatenate(frames)
    assert len(dates)==len(set(dates)) and dates==sorted(dates)
    files=[]
    for i in range(a.shape[1]):
        name=f'{i}.i16';(output/name).write_bytes(a[:,i].tobytes())
        files.append({'file':name,'bytes':a[:,i].nbytes,'sha256':hashlib.sha256(a[:,i].tobytes()).hexdigest()})
    metadata={'source':'Original NOAA OISST v2.1 daily SST files used by the habitat study','units':'degC','scale':.01,'missing':-32768,'encoding':'little-endian int16','dates':dates,'cells':cells,'files':files,'period':[dates[0],dates[-1]],'observed':True}
    (output/'index.json').write_text(json.dumps(metadata,separators=(',',':')))
    print(f'{a.shape[0]} days, {a.shape[1]} source cells',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--cells',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--pattern',required=True);args=p.parse_args()
    extract(args.source,json.loads(args.cells.read_text()),args.output,args.pattern)
