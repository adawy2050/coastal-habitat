"""Attach existing analysed marine SST histories to kelp model stations.

No new event detection, SST interpolation, or kelp fitting. The nearest retained
native source is accepted within 25 km for OISST and 5 km for MUR. Coordinate,
distance, baseline, and partial-year coverage accompany each point.
"""
from pathlib import Path
import gzip,json,hashlib
import numpy as np
from scipy.spatial import cKDTree
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'dist';OUT=D/'kelp/data/heatwaves'
METRICS=['mhw_days','mhw_frequency','mhw_mean_duration','mhw_mean_intensity','mhw_max_intensity','mhw_cumulative_intensity']

def xyz(a):
 a=np.deg2rad(a);return np.c_[np.cos(a[:,1])*np.cos(a[:,0]),np.cos(a[:,1])*np.sin(a[:,0]),np.sin(a[:,1])]

def clean(a):return [round(float(v),6) if np.isfinite(v) else None for v in a]

def main():
 OUT.mkdir(parents=True,exist_ok=True)
 stations=json.loads((D/'kelp/data/catalogue.json').read_text(encoding='utf-8'))['stations'];meta=json.loads((D/'data/metadata.json').read_text());monthly=json.loads((D/'detail/monthly/index.json').read_text());points=xyz([[s['lon'],s['lat']] for s in stations]);mapping={s['id']:{} for s in stations};audit={}
 for product,tolerance in [('oisst',25.),('mur',5.)]:
  info=meta['products'][product];cells=np.asarray(info['cells']);distance,index=cKDTree(xyz(cells)).query(points);km=2*np.arcsin(distance/2)*6371;accepted=km<=tolerance;unique=np.unique(index[accepted]);years=info['years'];width=len(cells)
  annual={metric:np.fromfile(D/f'data/{product}_{metric}.f32',dtype='<f4').reshape(len(years),width)[:,unique] for metric in METRICS}
  obs=json.loads((D/f'observed2026/{product}/index.json').read_text());current=np.frombuffer(gzip.decompress((D/f'observed2026/{product}'/obs['metricsFile']).read_bytes()),dtype='<f4').reshape(width,6)[unique]
  current_months=np.frombuffer(gzip.decompress((D/f'observed2026/{product}'/obs['monthlyFile']).read_bytes()),dtype='u1').reshape(width,-1)[unique]
  p=monthly['products'][product];chunk_width=monthly['chunkCells'];cache={};source_checks=[]
  for k,source in enumerate(unique):
   chunk=int(source//chunk_width)
   if chunk not in cache:
    cache.clear();cache[chunk]=np.fromfile(D/f'detail/monthly/{product}_{chunk}.u8',dtype='u1').reshape(-1,len(p['dates']))
   counts=cache[chunk][source%chunk_width].copy()
   # Native monthly counts must reproduce every original annual day total.
   sums=np.array([sum(int(v) for date,v in zip(p['dates'],counts) if date.startswith(str(y))) for y in years])
   np.testing.assert_array_equal(sums,annual['mhw_days'][:,k])
   np.testing.assert_equal(current_months[k].sum(),current[k,0])
   record={'product':product,'name':info['name'],'resolution':info['resolution'],'baseline':info['baseline'],'sourceIndex':int(source),'coordinate':cells[source].tolist(),'observedThrough':obs['dateEnd'],
    'annual':{'years':years+[2026],'metrics':{m:clean(np.r_[annual[m][:,k],current[k,i]]) for i,m in enumerate(METRICS)},'partialYear':2026,'partialThrough':obs['dateEnd']},
    'monthly':{'dates':[s[:7] for s in p['dates']]+[s[:7] for s in obs['monthDates']],'mhwDays':np.r_[counts,current_months[k]].astype(int).tolist(),'partialMonth':obs['dateEnd'][:7]},
    'note':'2026 is observed to date. MUR 2026 frequency/duration describe within-year event segments; earlier years retain the atlas definitions. SST exposure is independent of the kelp simulation forcing.'}
   path=OUT/f'{product}_{source}.json.gz';raw=json.dumps(record,separators=(',',':'),allow_nan=False).encode();path.write_bytes(gzip.compress(raw,compresslevel=8,mtime=0));source_checks.append(int(source))
  for i,s in enumerate(stations):mapping[s['id']][product]={'available':bool(accepted[i]),'distanceKm':round(float(km[i]),4),'maximumDistanceKm':tolerance,'sourceIndex':int(index[i]),'coordinate':cells[index[i]].tolist(),'file':f'{product}_{index[i]}.json.gz' if accepted[i] else None}
  audit[product]={'acceptedStations':int(accepted.sum()),'unavailableStations':int((~accepted).sum()),'nativeHistories':len(unique),'maxAcceptedDistanceKm':float(km[accepted].max()),'monthlyAnnualChecks':len(source_checks)*len(years)}
 manifest={'reviewed':'2026-11-02','method':'Nearest retained analysed marine SST source; no interpolation or new event detection. OISST <=25 km; MUR <=5 km. Distances are great-circle distances.','stations':mapping,'audit':audit,'sourceManifestSha256':hashlib.sha256((D/'data/manifest.json').read_bytes()).hexdigest()}
 (OUT/'index.json').write_bytes(json.dumps(manifest,separators=(',',':')).encode());(ROOT/'qa/kelp_heatwave_export.json').write_text(json.dumps({'passed':True,**audit},indent=2));print(json.dumps(audit,indent=2))

if __name__=='__main__':main()
