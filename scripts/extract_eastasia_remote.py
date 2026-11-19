"""Read archived East Asia heatwave states; write a separate habitat-only package.

No source files are changed. Temperature intensity is calculated in degrees C
relative to the saved 90th-percentile threshold; the integer exceedance flag is
never treated as temperature. Run on the study server with --input and --output.
"""
import argparse, json, re
from pathlib import Path
import numpy as np
import pandas as pd
from netCDF4 import Dataset, num2date
from scipy.ndimage import binary_dilation
from scipy.spatial import cKDTree

METRICS=['mhw_days','mhw_frequency','mhw_mean_duration','mhw_mean_intensity','mhw_max_intensity','mhw_cumulative_intensity']
ROOTS={'mur':Path('/minamitori/data1/eladawy/ANALYSISGHRSST/BASIC_HOBDAY_t192_w8/tiles'),
       'oisst':Path('/minamitori/data1/eladawy/OISST_HOBDAY_1982_2025_BASE1982_2011/tiles')}
def xyz(lon,lat):
    a,b=np.deg2rad(lon),np.deg2rad(lat)
    return np.column_stack([np.cos(a)*np.cos(b),np.sin(a)*np.cos(b),np.sin(b)])
def bounds(path):return tuple(map(int,re.search(r'lat(\d+)-(\d+)_lon(\d+)-(\d+)',path.name).groups()))
def read(v):return np.ma.filled(v,np.nan)
def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    out=args.output;out.mkdir(parents=True,exist_ok=True)
    sites=pd.read_csv(args.input);results={};checks=[]
    for product,root in ROOTS.items():
        cached=out/f'{product}_mapping.npz'
        if cached.exists():
            z=np.load(cached);ii,jj,dist,lon,lat=[z[k] for k in ['i','j','distance','lon','lat']]
        else:
            candidates=[]
            for path in sorted(root.glob('*clim_seas*nc')):
                a,b,c,d=bounds(path)
                with Dataset(path) as ds:
                    la=ds['lat'][:];lo=ds['lon'][:]
                    if product=='mur':
                        keep=(sites.lat_idx>=a-6)&(sites.lat_idx<b+6)&(sites.lon_idx>=c-6)&(sites.lon_idx<d+6)
                        if not keep.any():continue
                        near=np.zeros((b-a,d-c),bool)
                        si=sites.loc[keep,'lat_idx'].to_numpy(int)-a;sj=sites.loc[keep,'lon_idx'].to_numpy(int)-c
                        for di in range(-6,7):
                            for dj in range(-6,7):
                                x,y=si+di,sj+dj;ok=(x>=0)&(x<b-a)&(y>=0)&(y<d-c);near[x[ok],y[ok]]=True
                    else:near=np.ones((b-a,d-c),bool)
                    v=read(ds['climatology_c'][0]);x,y=np.where(np.isfinite(v)&near)
                    candidates.append(np.column_stack([x+a,y+c,lo[y],la[x]]))
            candidate=np.concatenate(candidates);tree=cKDTree(xyz(candidate[:,2],candidate[:,3]));distance,pos=tree.query(xyz(sites.lon,sites.lat))
            ii,jj=candidate[pos,0].astype(int),candidate[pos,1].astype(int);dist=2*6371*np.arcsin(np.minimum(distance/2,1));lon,lat=candidate[pos,2],candidate[pos,3]
            np.savez(cached,i=ii,j=jj,distance=dist,lon=lon,lat=lat)
        # Same retained habitat locations in both products; MUR marine attachment <=5 km.
        results[product]=(ii,jj,dist,lon,lat)
    keep=results['mur'][2]<=5.;sites.loc[keep].to_csv(out/'sites.csv',index=False)
    print('RETAINED',int(keep.sum()),'excluded',int((~keep).sum()),flush=True)
    for product,root in ROOTS.items():
        ii,jj,dist,lon,lat=[v[keep] for v in results[product]];nx=5001 if product=='mur' else 320
        flat=ii*nx+jj;cells,inverse=np.unique(flat,return_inverse=True);ci,cj=cells//nx,cells%nx;n=len(cells)
        np.savez(out/f'{product}_attachment.npz',index=inverse,distance=dist,cells=np.column_stack([lon[np.unique(flat,return_index=True)[1]],lat[np.unique(flat,return_index=True)[1]]]),flat=cells)
        for path in sorted(root.glob('*daily_state*nc')):
            a,b,c,d=bounds(path);take=np.flatnonzero((ci>=a)&(ci<b)&(cj>=c)&(cj<d))
            if not len(take):continue
            prefix=path.name.split('_mhw_daily')[0];checkpoint=out/f'{product}_{prefix}.npz'
            if checkpoint.exists():print('CACHED',checkpoint.name,flush=True);continue
            climpath=next(root.glob(prefix+'*clim_seas*nc'));threshpath=next(root.glob(prefix+'*clim_thresh*nc'))
            x,y=ci[take]-a,cj[take]-c
            with Dataset(climpath) as cd,Dataset(threshpath) as td:
                cv=next(v for k,v in cd.variables.items() if len(v.dimensions)==3);tv=next(v for k,v in td.variables.items() if len(v.dimensions)==3)
                clim=read(cv[:])[:,x,y];threshold=read(tv[:])[:,x,y]
            with Dataset(path) as ds:
                date=pd.DatetimeIndex([str(t)[:10] for t in num2date(ds['time'][:],ds['time'].units,only_use_cftime_datetimes=False)])
                nt=len(date);mask=np.empty((nt,len(take)),bool);intensity=np.empty((nt,len(take)),np.float32)
                doy=date.dayofyear.to_numpy()-1-((date.is_leap_year)&(date.month>2))
                for start in range(0,nt,31):
                    stop=min(start+31,nt)
                    mv=ds['mhw_mask'][start:stop];av=ds['anomaly_c'][start:stop]
                    mask[start:stop]=np.ma.filled(mv[:,x,y],0)>0
                    intensity[start:stop]=read(av[:,x,y])+clim[doy[start:stop]]-threshold[doy[start:stop]]
            years=np.arange(date.year.min(),date.year.max()+1);monthly=np.zeros((len(years)*12,len(take)),np.uint8);arrays={m:np.full((len(years),len(take)),np.nan,np.float32) for m in METRICS}
            previous=np.zeros_like(mask);previous[1:]=mask[:-1];gaps=np.r_[True,(np.diff(date.values).astype('timedelta64[D]').astype(int)>1)|(date.year[1:]!=date.year[:-1])];starts=mask&(~previous|gaps[:,None])
            for k,year in enumerate(years):
                sel=date.year==year;m=mask[sel];v=intensity[sel];days=m.sum(0);frequency=starts[sel].sum(0);cumulative=np.where(m,v,0).sum(0)
                arrays['mhw_days'][k]=days;arrays['mhw_frequency'][k]=frequency;arrays['mhw_cumulative_intensity'][k]=cumulative
                arrays['mhw_mean_duration'][k]=np.divide(days,frequency,out=np.full(len(take),np.nan),where=frequency>0)
                arrays['mhw_mean_intensity'][k]=np.divide(cumulative,days,out=np.full(len(take),np.nan),where=days>0)
                has=days>0
                if has.any():arrays['mhw_max_intensity'][k,has]=np.nanmax(np.where(m[:,has],v[:,has],np.nan),axis=0)
                for month in range(1,13):monthly[k*12+month-1]=mask[(date.year==year)&(date.month==month)].sum(0)
            assert np.array_equal(monthly.reshape(len(years),12,-1).sum(1),arrays['mhw_days'])
            np.savez_compressed(checkpoint,take=take,years=years,monthly=monthly,**arrays)
            print('EXTRACTED',product,prefix,len(take),flush=True)
        years=np.arange(2003 if product=='mur' else 1982,2026);monthly=np.zeros((len(years)*12,n),np.uint8);arrays={m:np.full((len(years),n),np.nan,np.float32) for m in METRICS};covered=np.zeros(n,bool)
        for path in out.glob(f'{product}_tile_*.npz'):
            z=np.load(path);take=z['take'];covered[take]=True;monthly[:,take]=z['monthly']
            for m in METRICS:arrays[m][:,take]=z[m]
        assert covered.all() and np.isfinite(arrays['mhw_days']).all()
        for m in METRICS:arrays[m].astype('<f4').tofile(out/f'{product}_{m}.f32')
        np.save(out/f'{product}_monthly.npy',monthly)
        checks.append({'product':product,'cells':n,'monthlyAnnualDaysEqual':True,'intensityUnits':'signed degrees C relative to saved p90 threshold, including joined gap days','years':years.tolist()})
    (out/'validation.json').write_text(json.dumps({'inputSites':int(len(keep)),'retainedSites':int(keep.sum()),'excludedBeyond5km':int((~keep).sum()),'checks':checks,'missingMurDates':['2021-02-20','2021-02-21','2022-11-09'],'sourceRoots':{k:str(v) for k,v in ROOTS.items()}}))
    print('COMPLETE',flush=True)
if __name__=='__main__':main()
