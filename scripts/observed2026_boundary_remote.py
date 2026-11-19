"""Confirm the December 2025 tail using January 2026, without changing archives.

The difference between a truncated and extended detection uses identical
December inputs, so the unknown November context cancels. Only extra days at
the previous record's right boundary are added to the complete DJF outcome.
"""
from pathlib import Path
import argparse,gzip,hashlib,json
import numpy as np
import pandas as pd
from netCDF4 import Dataset
from worker import mask_for

def main():
    a=argparse.ArgumentParser();a.add_argument('--root',type=Path,required=True);root=a.parse_args().root
    meta=json.loads((root/'metadata.json').read_text());public=root/'public';mf=json.loads((public/'manifest.json').read_text())
    dates=pd.date_range('2025-12-01','2026-01-12');doy=dates.dayofyear.to_numpy()-1
    for product in mf['products']:
        folder=public/product;ix=json.loads((folder/'index.json').read_text());target=folder/'previous_december_tail_additional_days.u8.gz'
        if target.exists() and ix.get('previousDecemberTailAdditionalDaysFile'):continue
        n=len(meta['products'][product]['cells']);values=np.full((len(dates),n),np.nan,np.float32)
        if product=='mur':
            for path in (root/'downloads').glob('mur_*.npz'):
                with np.load(path) as z:values[:,z['take']]=z['values'][:len(dates)]
        else:
            cells=np.array(meta['products'][product]['cells'])
            for k,date in enumerate(dates):
                with Dataset(root/'downloads'/f'oisst_{date:%Y%m%d}.nc') as nc:
                    lat=np.array(nc['lat'][:]);lon=np.array(nc['lon'][:]);v=np.ma.filled(nc['sst'][0,0],np.nan)
                    yy=np.abs(lat[:,None]-cells[:,1]).argmin(0);xx=np.abs(lon[:,None]-cells[:,0]).argmin(0);values[k]=v[yy,xx]
        assert np.isfinite(values).all()
        threshold=np.load(root/'baseline'/f'{product}_threshold.npy',mmap_mode='r');delta=np.zeros(n,dtype='u1')
        for basin,(start,end) in meta['products'][product]['basinCellRanges'].items():
            for lo in range(start,end,512):
                hi=min(end,lo+512);above=values[:,lo:hi]>threshold[doy,lo:hi]
                truncated=mask_for(above[:31],basin=='eastasia');extended=mask_for(above,basin=='eastasia')[:31]
                assert np.all(extended>=truncated)
                changed=extended.astype('i2')-truncated.astype('i2');assert not changed[:25].any()
                delta[lo:hi]=changed.sum(0)
        assert delta.max()<=6
        target.write_bytes(gzip.compress(delta.tobytes(),mtime=0));ix['previousDecemberTailAdditionalDaysFile']=target.name
        ix['previousDecemberTailNote']='Additional December 2025 MHW days confirmed by January 2026. Added only to the new complete DJF training outcome; archived annual/monthly study arrays are unchanged.'
        (folder/'index.json').write_text(json.dumps(ix,separators=(',',':')))
        checks={str(p.relative_to(public)):hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.rglob('*') if p.is_file() and p.name!='checksums.json'}
        (folder/'checksums.json').write_text(json.dumps(checks,separators=(',',':')))
        print(product,'boundary confirmed; changed cells',int((delta>0).sum()),'maximum extra December days',int(delta.max()),flush=True)
    mf['files']={str(p.relative_to(public)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in public.rglob('*') if p.is_file() and p.name!='manifest.json'}
    (public/'manifest.json').write_text(json.dumps(mf,separators=(',',':')))

if __name__=='__main__':main()
