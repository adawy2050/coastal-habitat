"""Build habitat-source-cell seasonal outcomes for individual-pixel forecasts."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'dist/data'
ORIGINAL=ROOT.parent/'redsea_ghrsst_habitat/data/derived'
MONTH_START=np.r_[0,np.cumsum([31,28,31,30,31,30,31,31,30,31,30,31])]


def monthly(product,metadata):
    cache=ROOT/'_cache'/f'{product}_monthly_pixels.npy'
    info=metadata['products'][product];years=np.array(info['years']);nx=2151 if product=='mur' else 86
    native=info['cells']
    if product=='mur':
        cell=np.array([int(round((lat-9.5)*100))*2151+int(round((lon-31)*100)) for lon,lat in native])
    else:
        cell=np.array([int(round((lat-9.625)/.25))*86+int(round((lon-31.125)/.25)) for lon,lat in native])
    assert (np.diff(cell)>0).all()
    if cache.exists():return np.load(cache)
    event=ORIGINAL/('ghrsst_summary/ghrsst_mhw_events_analysis_domain.parquet' if product=='mur' else 'oisst/oisst_mhw_events.parquet')
    starts=np.array([y*365+MONTH_START[m] for y in years for m in range(12)])
    ends=np.r_[starts[1:],(years[-1]+1)*365]
    result=np.zeros((len(starts),len(cell)),dtype=np.float32)
    fields=['lat_idx','lon_idx','start_year','end_year','start_doy','end_doy','duration_days']
    used=0
    for k,batch in enumerate(pq.ParquetFile(event).iter_batches(columns=fields,batch_size=1_000_000)):
        frame=batch.to_pandas()
        cells=frame.lat_idx.to_numpy(np.int64)*nx+frame.lon_idx.to_numpy(np.int64)
        positions=np.searchsorted(cell,cells)
        keep=(positions<len(cell))&(cell[np.minimum(positions,len(cell)-1)]==cells)
        if not keep.any():continue
        frame=frame.loc[keep];positions=positions[keep]
        s=frame.start_year.to_numpy(np.int64)*365+frame.start_doy.to_numpy(np.int64)-1
        e=frame.end_year.to_numpy(np.int64)*365+frame.end_doy.to_numpy(np.int64)
        assert np.all(e-s==frame.duration_days.to_numpy())
        first=np.searchsorted(ends,s,side='right');last=np.searchsorted(starts,e-1,side='right')-1
        for offset in range(int((last-first).max())+1):
            month=first+offset;ok=(month<=last)&(month>=0)&(month<len(starts));m=month[ok]
            days=np.minimum(e[ok],ends[m])-np.maximum(s[ok],starts[m])
            np.add.at(result,(m,positions[ok]),days)
        used+=len(frame)
        if k%8==0:print(product,'monthly batch',k,'events',used,flush=True)
    result=result.reshape(len(years),12,len(cell))
    annual=np.fromfile(DATA/f'{product}_mhw_days.f32',dtype='<f4').reshape(len(years),len(cell))
    assert np.max(np.abs(result.sum(axis=1)-annual))<1e-4
    assert result.min()>=0 and np.all(result<=np.diff(MONTH_START)[None,:,None])
    np.save(cache,result)
    return result


def main():
    meta=json.loads((DATA/'metadata.json').read_text());points=np.array(json.loads((DATA/'pixels.json').read_text())['rows'])
    groups=[{'scope':'overall','habitat':h,'region':'All study ecoregions'} for h in meta['habitats']]
    groups +=[{'scope':'ecoregion','habitat':h,'region':r} for r in meta['regions'] for h in meta['habitats']]
    group_data={'groups':groups,'products':{}}
    checks=[]
    reference=pd.read_csv(ROOT.parent/'revision_round1/03_analyses/seasonal_habitat_alerts/monthly_habitat_mhw_days.csv')
    for product in ['mur','oisst']:
        a=monthly(product,meta);info=meta['products'][product];n=len(info['cells']);ny=len(info['years']);weights=[]
        for group in groups:
            habitat=meta['habitats'].index(group['habitat']);keep=(points[:,2].astype(int)&(1<<habitat))!=0
            if group['scope']=='ecoregion':keep&=points[:,3]==meta['regions'].index(group['region'])
            weight=np.bincount(points[keep,4 if product=='mur' else 5].astype(int),minlength=n)/keep.sum()
            weights.append(weight)
            if group['scope']=='ecoregion':
                observed=a.reshape(ny*12,n)@weight
                r=reference[(reference['product']==info['name'])&(reference.habitat==group['habitat'])&(reference.region==group['region'])].sort_values(['year','month'])
                diff=float(np.max(np.abs(observed-r.mhw_days.to_numpy())))
                assert diff<1e-4,diff
                checks.append({'product':product,**group,'maxMonthlyDifference':diff})
        weights=np.array(weights).T
        seasons={}
        for season,start in [('MAM',2),('JJA',5),('SON',8),('DJF',11)]:
            if start<11:values=a[:,start:start+3,:].sum(axis=1)
            else:
                values=np.full((ny,n),np.nan,dtype=np.float32)
                values[:-1]=a[:-1,11,:]+a[1:,0,:]+a[1:,1,:]
            values.astype('<f4').tofile(DATA/f'{product}_season_{season}.f32')
            group_values=values@weights
            seasons[season]=[[None if not np.isfinite(v) else float(v) for v in row] for row in group_values]
        group_data['products'][product]={'years':info['years'],'seasons':seasons}
        print(product,'seasonal pixel histories ready',flush=True)
    (DATA/'seasonal_groups.json').write_text(json.dumps(group_data,separators=(',',':')),encoding='utf-8')
    (DATA/'seasonal_pixel_validation.json').write_text(json.dumps({'checks':checks,'annualDaysReconstructionPassed':True},indent=2))


if __name__=='__main__':main()
