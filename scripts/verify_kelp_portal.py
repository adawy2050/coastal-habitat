"""Read source files independently and check sampled display values and maps."""
from pathlib import Path
import gzip,json,struct,hashlib
import numpy as np
import pandas as pd
import xarray as xr
from package_kelp_maps import decode
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'dist/kelp/data'
L=Path('D:/kep model/kelp_paper_revision_20260306/ssp_model_runs_20261020/manuscript_TPM20p43_20261021')
J=Path('D:/kep model/otherspeciesmodels/Saccharina_japonica_focus/32_Japonica_1931_model_ready_20261008/outputs_1991_2020_higher_mixedNO3')

def monthly(path):
 raw=gzip.decompress(path.read_bytes());m,y,f,a=struct.unpack('<4I',raw[:16]);scales=np.frombuffer(raw,dtype='<f8',count=f+a,offset=16);q=np.frombuffer(raw,dtype='<u2',count=m*f,offset=16+8*(f+a)).reshape(m,f)
 return np.where(q==65535,np.nan,q*scales[:f]),scales[:f]/2

def main():
 j=json.loads((D/'catalogue.json').read_text(encoding='utf-8'));assert len(j['stations'])==2029
 assert not any(s['id']=='JAP_OCC_000010' for s in j['stations'])
 n=0
 for station in j['stations']:
  for key,file in station['files'].items():
   assert hashlib.sha256((D/file).read_bytes()).hexdigest()==station['displaySha256'][key];n+=1
 assert n==2227
 samples=[]
 for species,meta in j['species'].items():
  stations=[s for s in j['stations'] if s['species']==species]
  for scenario,record in meta['scenarios'].items():
   info=j['maps'][species][scenario];maps=np.frombuffer(gzip.decompress((D/info['file']).read_bytes()),dtype='<f4').reshape(info['shape'])
   for index in [0,len(stations)//2,len(stations)-1]:
    s=stations[index];a=decode(D/s['files'][scenario]);np.testing.assert_allclose(maps[:,index],a,rtol=1e-7,atol=1e-6,equal_nan=True)
    values,bounds=monthly(D/s['files'][scenario]);field=j['monthlyFields'].index('mass')
    if species=='japonica':
     native=pd.read_csv(J/s['id']/'daily.csv',usecols=['date','B_gDW_thallus'],parse_dates=['date']).set_index('date').iloc[:,0].resample('MS').mean().to_numpy()
    else:
     blocks=['1996_2000','2001_2020'] if scenario=='historical' else [None];arrays=[]
     for block in blocks:
      path=L/f'historical/kelp_output_{block}_corrected_Io180.nc' if block else L/f'future/{scenario.upper()}/results/outputs/kelp_{scenario.upper()}_MI_99stations_2021_2100.nc'
      with xr.open_dataset(path) as ds:
       ids=np.asarray(ds['station' if block else 'station_id']);position=int(np.flatnonzero(ids==int(s['id']))[0]);clock=ds['time' if block else 'day_time'].values
       arrays.append(pd.Series(np.asarray(ds.B_daily_mean[:,position]),index=pd.DatetimeIndex(clock)).resample('MS').mean())
     native=pd.concat(arrays).to_numpy()
    error=float(np.max(abs(values[:,field]-native)));assert error<=bounds[field]+1e-7
    samples.append({'species':species,'scenario':scenario,'station':s['id'],'monthlyMassMaxError':error,'roundingBound':float(bounds[field])})
 output={'passed':True,'pointRecordsVerified':n,'independentNativeSamples':samples}
 (ROOT/'qa/kelp_independent_validation.json').write_text(json.dumps(output,indent=2));print('PASS:',n,'point checksums; 12 independent native monthly-mass and annual-map comparisons.')

if __name__=='__main__':main()
