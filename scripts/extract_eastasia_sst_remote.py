"""Extract original daily OISST at the same retained East Asia marine cells."""
from pathlib import Path
import argparse,json
import numpy as np,pandas as pd
from netCDF4 import Dataset,num2date

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args();out=args.output
    m=np.load(out/'mur_mapping.npz');o=np.load(out/'oisst_mapping.npz');keep=m['distance']<=5
    flat=o['i'][keep]*320+o['j'][keep];cells,index=np.unique(flat,return_inverse=True);first=np.unique(flat,return_index=True)[1];ii,jj=cells//320,cells%320;n=len(cells)
    np.savez(out/'oisst_attachment.npz',index=index,distance=o['distance'][keep],cells=np.column_stack([o['lon'][keep][first],o['lat'][keep][first]]),flat=cells)
    daily=[];dates=[];annual=[]
    for year in range(1982,2026):
        cache=out/f'oisst_raw_{year}.npz'
        if cache.exists():z=np.load(cache);v=z['values'];ds=z['dates'].tolist()
        else:
            path=Path(f'/minamitori/data1/eladawy/OISST_100E_180E_0N_70N_sst_anom_198109_202512/oisst_100E_180E_0N_70N_{year}.nc')
            with Dataset(path) as source:
                ds=[str(t)[:10] for t in num2date(source['time'][:],source['time'].units,only_use_cftime_datetimes=False)]
                raw=source['sst'][:];v=np.ma.filled(raw[:,ii,jj],np.nan)
                assert np.isfinite(v).all(),(year,'missing marine SST')
            np.savez_compressed(cache,values=v,dates=ds)
        daily.append(np.round(v*100).astype('<i2'));annual.append(np.mean(v,axis=0));dates.extend(ds);print('DAILY SST',year,n,flush=True)
    allvalues=np.concatenate(daily);assert len(dates)==16071
    np.savez_compressed(out/'oisst_daily.npz',values=allvalues,dates=dates)
    np.array(annual,dtype='<f4').tofile(out/'oisst_sst.f32')
    print('DAILY COMPLETE',allvalues.shape,flush=True)
if __name__=='__main__':main()
