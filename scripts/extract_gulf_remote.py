"""Extract habitat-only Gulf arrays on the study server; never edit source data.

python extract_gulf_remote.py --root STUDY_ROOT --output NEW_ATLAS_CACHE
The output is a compact transfer package, not a new SST/MHW detection run.
"""
from pathlib import Path
import argparse
import json
import re
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import xarray as xr
from scipy.spatial import cKDTree

METRICS=['mhw_days','mhw_frequency','mhw_mean_duration','mhw_mean_intensity','mhw_max_intensity','mhw_cumulative_intensity']
REGIONS=['Arabian (Persian) Gulf','Gulf of Oman']
MONTH=np.r_[0,np.cumsum([31,28,31,30,31,30,31,31,30,31,30,31])]


def xyz(lon,lat):
    lon,lat=np.deg2rad(lon),np.deg2rad(lat)
    return np.column_stack([np.cos(lat)*np.cos(lon),np.cos(lat)*np.sin(lon),np.sin(lat)])


def attach(sites,path,variable):
    with xr.open_dataset(path) as ds:
        valid=np.isfinite(ds[variable].isel(time=0).values)
        lat,lon=ds.lat.values,ds.lon.values
    i,j=np.where(valid)
    tree=cKDTree(xyz(lon[j],lat[i]))
    distance,pos=tree.query(xyz(sites.lon.to_numpy(),sites.lat.to_numpy()))
    return i[pos],j[pos],2*6371*np.arcsin(np.minimum(distance/2,1)),lon,lat


def monthly(root,product,cell,nx,years,output):
    cache=output/f'{product}_monthly_native.npy'
    if cache.exists():return np.load(cache)
    path=root/('data/derived/ghrsst_mhw_events.parquet' if product=='mur' else 'data/derived/oisst/oisst_mhw_events.parquet')
    starts=np.array([y*365+MONTH[m] for y in years for m in range(12)])
    ends=np.r_[starts[1:],(years[-1]+1)*365]
    result=np.zeros((len(starts),len(cell)),dtype=np.float32)
    fields=['lat_idx','lon_idx','start_year','end_year','start_doy','end_doy','duration_days']
    used=0
    for k,batch in enumerate(pq.ParquetFile(path).iter_batches(columns=fields,batch_size=750000)):
        frame=batch.to_pandas();flat=frame.lat_idx.to_numpy(np.int64)*nx+frame.lon_idx.to_numpy(np.int64)
        pos=np.searchsorted(cell,flat);ok=(pos<len(cell))&(cell[np.minimum(pos,len(cell)-1)]==flat)
        if not ok.any():continue
        frame=frame.loc[ok];pos=pos[ok]
        s=frame.start_year.to_numpy(np.int64)*365+frame.start_doy.to_numpy(np.int64)-1
        e=frame.end_year.to_numpy(np.int64)*365+frame.end_doy.to_numpy(np.int64)
        assert np.all(e-s==frame.duration_days.to_numpy())
        first=np.searchsorted(ends,s,side='right');last=np.searchsorted(starts,e-1,side='right')-1
        for offset in range(int((last-first).max())+1):
            m=first+offset;take=(m<=last)&(m>=0)&(m<len(starts));mi=m[take]
            days=np.minimum(e[take],ends[mi])-np.maximum(s[take],starts[mi])
            np.add.at(result,(mi,pos[take]),days)
        used+=len(frame)
        if k%6==0:print(product,'event batch',k,'habitat events',used,flush=True)
    result=result.reshape(len(years),12,len(cell))
    np.save(cache,result)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=args.root.resolve();out=args.output.resolve()
    assert root!=out and root not in out.parents or out.name.startswith('atlas_extract')
    out.mkdir(parents=True,exist_ok=True)
    records=pd.read_parquet(root/'data/derived/habitat_sites_ghrsst.parquet')
    excluded_regions=int((~records.meow_ecoregion.isin(REGIONS)).sum())
    records=records[records.meow_ecoregion.isin(REGIONS)].drop_duplicates(['grid_site_id','habitat_group'])
    sites=records.drop_duplicates('grid_site_id').sort_values(['lat_idx','lon_idx']).reset_index(drop=True)
    murfile=next((root/'data/raw/ghrsst_daily').glob('20030101*.nc'))
    oisstfile=root/'data/raw/oisst_yearly/oisst_v2_1_arabian_persian_gulf_1982.nc'
    mi,mj,md,mlon,mlat=attach(sites,murfile,'analysed_sst')
    oi,oj,od,olon,olat=attach(sites,oisstfile,'sst')
    keep=md<=5
    counts={'inputUniqueSites':len(sites),'inputHabitatRecords':len(records),'excludedBeyond5km':int((~keep).sum()),'reattachedMurSites':int(((md>.01)&keep).sum()),'excludedUnknownRecords':excluded_regions}
    sites=sites.loc[keep].copy().reset_index(drop=True)
    mi,mj,md,oi,oj,od=[a[keep] for a in [mi,mj,md,oi,oj,od]]
    records=records[records.grid_site_id.isin(sites.grid_site_id)]
    mur=np.unique(mi*len(mlon)+mj);oisst=np.unique(oi*len(olon)+oj)
    mapping={row.grid_site_id:i for i,row in sites.iterrows()}
    bits=records.assign(bit=records.habitat_group.map({'coral':1,'seagrass':2,'mangrove':4})).groupby('grid_site_id').bit.sum()
    rows=[[round(float(s.lon),2),round(float(s.lat),2),int(bits[s.grid_site_id]),REGIONS.index(s.meow_ecoregion),int(np.searchsorted(mur,mi[k]*len(mlon)+mj[k])),int(np.searchsorted(oisst,oi[k]*len(olon)+oj[k])),round(float(md[k]),3),round(float(od[k]),3),int(s.lat_idx),int(s.lon_idx)] for k,s in sites.iterrows()]
    (out/'pixels.json').write_text(json.dumps({'rows':rows},separators=(',',':')))
    products={}
    checks=[]
    for product,cells,lons,lats,nx in [('mur',mur,mlon,mlat,len(mlon)),('oisst',oisst,olon,olat,len(olon))]:
        years=np.arange(2003 if product=='mur' else 1982,2026)
        arrays={m:np.full((len(years),len(cells)),np.nan,dtype=np.float32) for m in METRICS}
        if product=='mur':
            for path in sorted((root/'data/derived/ghrsst_tiles').glob('*_mhw_annual_metrics.nc')):
                a,b,c,d=map(int,re.search(r'lat(\d+)-(\d+)_lon(\d+)-(\d+)',path.name).groups())
                take=np.flatnonzero((cells//nx>=a)&(cells//nx<b)&(cells%nx>=c)&(cells%nx<d))
                if len(take):
                    with xr.open_dataset(path) as ds:
                        ii=xr.DataArray(cells[take]//nx-a,dims='point');jj=xr.DataArray(cells[take]%nx-c,dims='point')
                        for m in METRICS:arrays[m][:,take]=ds[m].isel(lat=ii,lon=jj).values
                    print('MUR native arrays',path.name,len(take),flush=True)
        else:
            with xr.open_dataset(root/'data/derived/oisst/oisst_mhw_annual_metrics.nc') as ds:
                for m in METRICS:arrays[m]=ds[m].values[:,cells//nx,cells%nx].astype(np.float32)
            means=[]
            for year in years:
                with xr.open_dataset(root/f'data/raw/oisst_yearly/oisst_v2_1_arabian_persian_gulf_{year}.nc') as ds:
                    means.append(np.nanmean(ds.sst.values[:,cells//nx,cells%nx],axis=0))
            sst=np.array(means,dtype='<f4');assert np.isfinite(sst).all();sst.tofile(out/'oisst_sst.f32')
        for m,a in arrays.items():
            if m in ['mhw_days','mhw_frequency','mhw_cumulative_intensity']:assert np.isfinite(a).all() and (a>=0).all()
            a.astype('<f4').tofile(out/f'{product}_{m}.f32')
        monthly_values=monthly(root,product,cells,nx,years,out)
        diff=float(np.max(np.abs(monthly_values.sum(axis=1)-arrays['mhw_days'])))
        assert diff<1e-4,(product,diff)
        assert monthly_values.min()>=0 and np.all(monthly_values<=np.diff(MONTH)[None,:,None])
        for season,start in [('MAM',2),('JJA',5),('SON',8),('DJF',11)]:
            if start<11:value=monthly_values[:,start:start+3].sum(axis=1)
            else:
                value=np.full_like(arrays['mhw_days'],np.nan);value[:-1]=monthly_values[:-1,11]+monthly_values[1:,0]+monthly_values[1:,1]
            value.astype('<f4').tofile(out/f'{product}_season_{season}.f32')
        checks.append({'product':product,'annualMonthlyDaysMaxDifference':diff,'nativeCells':len(cells)})
        products[product]={'name':'GHRSST MUR' if product=='mur' else 'OISST','years':years.tolist(),'resolution':'0.01°' if product=='mur' else '0.25°','baseline':'2003–2022' if product=='mur' else '1982–2011','cells':[[round(float(lons[x%nx]),3),round(float(lats[x//nx]),3)] for x in cells]}
    counts.update(pixels=len(sites),habitatRecords=len(records),regions=REGIONS,products=products,checks=checks,attachmentRule='Nearest marine SST cell; MUR distance <=5 km; original annual tiles and native events; unique habitat-cell weights')
    (out/'metadata.json').write_text(json.dumps(counts,separators=(',',':')))
    records.to_parquet(out/'retained_records.parquet',index=False)
    print('GULF EXTRACTION READY',len(sites),'habitat cells',flush=True)


if __name__=='__main__':main()
