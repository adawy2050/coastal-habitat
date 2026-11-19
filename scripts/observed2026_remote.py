"""Resume habitat-only 2026 SST downloads and fixed-baseline heatwave analysis.
Run on the study server. All writes are contained in --root; archives are read-only.
"""
from pathlib import Path
import argparse, concurrent.futures, datetime as dt, gzip, hashlib, io, json, os, re, threading, time, traceback
import numpy as np
import pandas as pd
import requests
from scipy.io import netcdf_file
from netCDF4 import Dataset, num2date

ROOTS={
 'redsea':Path('/minamitori/data1/eladawy/GHRSST_REDSEA_MUR_v41/redsea_ghrsst_habitat/data/derived'),
 'gulf':Path('/minamitori/data2/eladawy/GHRSST_ARABIAN_GULF_MUR_v41/arabian_gulf_ghrsst_habitat/data/derived'),
 'eastasia_mur':Path('/minamitori/data1/eladawy/ANALYSISGHRSST/BASIC_HOBDAY_t192_w8/tiles'),
 'eastasia_oisst':Path('/minamitori/data1/eladawy/OISST_HOBDAY_1982_2025_BASE1982_2011/tiles')}
METRICS=['mhw_days','mhw_frequency','mhw_mean_duration','mhw_mean_intensity','mhw_max_intensity','mhw_cumulative_intensity']
LOCK=threading.Lock();STATUS={};ROOT=None

def stamp():return dt.datetime.now(dt.timezone.utc).isoformat()
def write_json(path,data):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,allow_nan=False,separators=(',',':')));tmp.replace(path)
def status(**kw):
 with LOCK:
  STATUS.update(kw);STATUS['updatedAt']=stamp();STATUS['jobs']=[dict(name=p,product=p,basin='all',stage=r.get('status'),**r) for p,r in STATUS.get('products',{}).items()];write_json(ROOT/'status.json',STATUS)
def progress(product,**kw):
 with LOCK:
  STATUS['products'][product].update(kw);STATUS['updatedAt']=stamp();STATUS['jobs']=[dict(name=p,product=p,basin='all',stage=r.get('status'),**r) for p,r in STATUS.get('products',{}).items()];write_json(ROOT/'status.json',STATUS)
def fetch(url,path,retries=5):
 if path.exists() and path.stat().st_size>100:return
 for attempt in range(retries):
  try:
   r=requests.get(url,timeout=(30,240),headers={'User-Agent':'CoastalHabitatMHWAtlas/2026 scientific habitat-cell update'});r.raise_for_status()
   if r.content[:3] not in [b'CDF',b'\x89HD']:raise ValueError('Response is not NetCDF')
   tmp=path.with_suffix('.part');tmp.write_bytes(r.content);tmp.replace(path);return
  except Exception:
   if attempt==retries-1:raise
   time.sleep(min(60,5*2**attempt))
def minrun(a,n=5):
 out=np.zeros(a.shape,bool)
 for j in range(a.shape[1]):
  x=np.flatnonzero(a[:,j]);splits=np.split(x,np.flatnonzero(np.diff(x)>1)+1)
  for s in splits:
   if len(s)>=n:out[s,j]=True
 return out
def mask_for(a,joined):
 # East Asia source joins gaps of at most two days first, then filters short events.
 out=a.copy()
 if joined:
  for j in range(out.shape[1]):
   ids=np.flatnonzero(a[:,j]);g=np.flatnonzero((np.diff(ids)>1)&(np.diff(ids)<=3))
   for k in g:out[ids[k]:ids[k+1]+1,j]=True
 return minrun(out)

def baseline(meta,product):
 out=ROOT/'baseline';out.mkdir(exist_ok=True);n=len(meta['products'][product]['cells']);cells=np.array(meta['products'][product]['cells']);paths={k:out/f'{product}_{k}.npy' for k in ['clim','threshold']}
 if all(p.exists() for p in paths.values()) and (out/f'{product}_validation.json').exists():
  validation=json.loads((out/f'{product}_validation.json').read_text())
  if all(c['maskDifferences']==0 for c in validation['checks']):return
 arrays={k:np.lib.format.open_memmap(p,mode='w+',dtype='float32',shape=(365,n)) for k,p in paths.items()}
 for a in arrays.values():a[:]=np.nan
 covered=np.zeros(n,bool);checks=[]
 for basin,(start,end) in meta['products'][product]['basinCellRanges'].items():
  part=cells[start:end];base=ROOTS.get(basin+'_'+product,ROOTS.get(basin));folder=base if basin=='eastasia' else base/('ghrsst_tiles' if product=='mur' else 'oisst')
  files=sorted(folder.glob('*clim_seas*nc')) if basin=='eastasia' or product=='mur' else sorted(folder.glob('*climatology_threshold*nc'))
  qc=[]
  for ix,p in enumerate(files):
   with Dataset(p) as d:
    lat=np.array(d['lat'][:]);lon=np.array(d['lon'][:]);take=np.flatnonzero((part[:,0]>=lon.min()-1e-4)&(part[:,0]<=lon.max()+1e-4)&(part[:,1]>=lat.min()-1e-4)&(part[:,1]<=lat.max()+1e-4))
    if not len(take):continue
    y=np.rint((part[take,1]-lat[0])/(lat[1]-lat[0])).astype(int);x=np.rint((part[take,0]-lon[0])/(lon[1]-lon[0])).astype(int)
    assert np.max(abs(lat[y]-part[take,1]))<.001 and np.max(abs(lon[x]-part[take,0]))<.001
    cv=np.ma.filled(d['climatology_c'][:],np.nan);cc=cv[:,y,x]
    if 'threshold_90_c' in d.variables:tv=np.ma.filled(d['threshold_90_c'][:],np.nan)
    else:
     prefix=p.name.split('_clim_seas')[0];tf=next(folder.glob(prefix+'*clim_thresh*nc'))
     with Dataset(tf) as t:tv=np.ma.filled(t['threshold_c'][:],np.nan)
    th=tv[:,y,x];arrays['clim'][:,start+take]=cc;arrays['threshold'][:,start+take]=th;covered[start+take]=True
   # Exact saved-state reproducibility on up to eight marine habitat cells per tile.
   prefix=p.name.split('_clim_seas')[0];daily=list(folder.glob(prefix+'*daily_state*nc'))
   if daily:
    choose=np.linspace(0,len(take)-1,min(8,len(take))).astype(int);xx,yy=x[choose],y[choose]
    with Dataset(daily[0]) as d:
     dates=pd.DatetimeIndex([str(v)[:10] for v in num2date(d['time'][:],d['time'].units,only_use_cftime_datetimes=False)]);sel=np.flatnonzero(dates.year>=2024);dates=dates[sel]
     an=np.ma.filled(d['anomaly_c'][int(sel[0]):][:,yy,xx],np.nan) if False else None
     # netCDF advanced indices are orthogonal; read one selected pixel at a time.
     an=np.column_stack([np.ma.filled(d['anomaly_c'][int(sel[0]):,int(i),int(j)],np.nan) for i,j in zip(yy,xx)])
     saved=np.column_stack([np.ma.filled(d['mhw_mask'][int(sel[0]):,int(i),int(j)],0)>0 for i,j in zip(yy,xx)])
     flag=np.column_stack([np.ma.filled(d['exceedance'][int(sel[0]):,int(i),int(j)],0)>0 for i,j in zip(yy,xx)]) if basin=='eastasia' else None
    doy=dates.dayofyear.to_numpy()-1-((dates.is_leap_year)&(dates.month>2));sst=an+cc[doy][:,choose];exc=sst-th[doy][:,choose];positive=exc>0;calc=mask_for(flag if basin=='eastasia' else positive,basin=='eastasia');interior=(dates.year==2025)&(dates.month<12)
    mismatch=int(np.count_nonzero(calc[interior]!=saved[interior]));record={'tile':p.name,'cells':len(choose),'days':int(interior.sum()),'maskDifferences':mismatch,'savedFlagMaskExact':mismatch==0}
    if basin=='eastasia':
     disagree=positive!=flag;near=float(np.max(abs(exc[disagree]))) if disagree.any() else 0.;record['packedThresholdCrossingDifferences']=int(disagree.sum());record['packedThresholdCrossingMaxAbsC']=near;assert near<=.025,(p.name,near)
     if product=='oisst':
      rawpath=Path('/minamitori/data1/eladawy/OISST_100E_180E_0N_70N_sst_anom_198109_202512/oisst_100E_180E_0N_70N_2025.nc')
      with Dataset(rawpath) as raw:
       rlat=np.array(raw['lat'][:]);rlon=np.array(raw['lon'][:]);ry=np.abs(rlat[:,None]-part[take[choose],1]).argmin(0);rx=np.abs(rlon[:,None]-part[take[choose],0]).argmin(0);rd=pd.DatetimeIndex([str(v)[:10] for v in num2date(raw['time'][:],raw['time'].units,only_use_cftime_datetimes=False)]);rv=np.column_stack([np.ma.filled(raw['sst'][:,int(i),int(j)],np.nan) for i,j in zip(ry,rx)]);keep=dates.year==2025;pos=rd.get_indexer(dates[keep]);assert (pos>=0).all();err=float(np.nanmax(abs(sst[keep]-rv[pos])));assert err<=.025,err;record['rawSST2025QuantizationMaxC']=err;record['rawSST2025Checks']=int(rv[pos].size)
    qc.append(record)
   progress(product,status='baseline',baselineTiles=ix+1,baselineCells=int(covered.sum()),message='Reading archived fixed climatology and checking saved 2025 events')
  checks.append({'basin':basin,'savedStateTests':qc,'maskDifferences':sum(q['maskDifferences'] for q in qc),'cells':end-start})
 assert covered.all(),int((~covered).sum())
 assert all(np.isfinite(a).all() for a in arrays.values()),'Non-finite baseline at a native habitat cell'
 for a in arrays.values():a.flush()
 write_json(out/f'{product}_validation.json',{'checkedAt':stamp(),'checks':checks,'allNativeCellsCovered':True})
 # Differences must be inspected rather than publishing a new convention silently.
 if any(c['maskDifferences'] for c in checks):progress(product,error='Saved-state differences need review',message='Downloads continue; analysis held pending source convention review')

def validate_old_oisst():
 z=np.load(ROOT/'oisst_old_raw2024_2025.npz');dates=pd.DatetimeIndex(z['dates']);keep=~((dates.month==2)&(dates.day==29));dates=dates[keep];v=z['values'][keep];threshold=np.load(ROOT/'baseline/oisst_threshold.npy',mmap_mode='r')[:,:483];d=dates.dayofyear.to_numpy()-1-((dates.is_leap_year)&(dates.month>2));mask=mask_for(v>threshold[d],False);got=mask[dates.year==2025].sum(0);want=np.load(ROOT/'oisst_old_2025_days.npy');assert np.array_equal(got,want),'2025 old-basin OISST daily SST does not reproduce original annual days'
 path=ROOT/'baseline/oisst_validation.json';j=json.loads(path.read_text());j['independentRawSST2025DaysChecks']={'redsea':325,'gulf':158,'exact':True,'maxAbsDifferenceDays':0};write_json(path,j)

def mur_jobs(meta,latest):
 cells=np.array(meta['products']['mur']['cells']);ij=np.rint(cells*100).astype(int);blocks=ij//32;keys=np.unique(blocks,axis=0);jobs=[]
 for k in keys:
  take=np.flatnonzero(np.all(blocks==k,axis=1));p=cells[take];west,south=p.min(0);east,north=p.max(0);name=f'mur_{k[0]}_{k[1]}';jobs.append({'name':name,'product':'mur','take':take,'bounds':[west,south,east,north],'path':ROOT/'downloads'/f'{name}.npz'})
 return jobs

def download_mur(job,latest):
 p=job['path']
 if p.exists():return
 w,s,e,n=job['bounds'];url=f'https://coastwatch.pfeg.noaa.gov/erddap/griddap/jplMURSST41.nc?analysed_sst[(2025-12-01T09:00:00Z):1:({latest}T09:00:00Z)][({s:.2f}):1:({n:.2f})][({w:.2f}):1:({e:.2f})]'
 raw=p.with_suffix('.nc');fetch(url,raw)
 with netcdf_file(raw,'r',mmap=False) as d:
  lat=d.variables['latitude'].data.copy();lon=d.variables['longitude'].data.copy();v=d.variables['analysed_sst'].data.copy();t=d.variables['time'].data.copy();units=d.variables['time'].units.decode()
  cells=np.array(META['products']['mur']['cells'])[job['take']];y=np.abs(lat[:,None]-cells[:,1]).argmin(0);x=np.abs(lon[:,None]-cells[:,0]).argmin(0);assert abs(lat[y]-cells[:,1]).max()<.001 and abs(lon[x]-cells[:,0]).max()<.001
  v=v[:,y,x].astype('float32');fill=getattr(d.variables['analysed_sst'],'_FillValue',-9999);v[v==fill]=np.nan
 dates=[str(x)[:10] for x in num2date(t,units,only_use_cftime_datetimes=False)]
 assert np.isfinite(v).all(),(job['name'],'missing marine SST')
 tmp=p.with_suffix('.part.npz');np.savez_compressed(tmp,values=v,take=job['take'],dates=dates,source=url);tmp.replace(p);raw.unlink()

def download_oisst(job,latest):
 date=job['date'];p=job['path'];day=date.replace('-','');base=f'https://www.ncei.noaa.gov/data/sea-surface-temperature-optimum-interpolation/v2.1/access/avhrr/{day[:6]}/oisst-avhrr-v02r01.{day}'
 if p.exists():return
 # Recent observations are explicitly preliminary; final records replace them upstream.
 recent=(pd.Timestamp(latest)-pd.Timestamp(date)).days<18
 urls=[base+('_preliminary.nc' if recent else '.nc'),base+('.nc' if recent else '_preliminary.nc')]
 raw=p;error=None
 for u in urls:
  try:fetch(u,raw,retries=2);break
  except Exception as ex:error=ex
 else:raise error
 write_json(p.with_suffix('.source.json'),{'url':u,'preliminary':'_preliminary' in u})

def analyse(meta,product,latest,jobs):
 validation=json.loads((ROOT/'baseline'/f'{product}_validation.json').read_text());assert all(c['maskDifferences']==0 for c in validation['checks']), 'Saved-state event validation needs review'
 out=ROOT/'public'/product;out.mkdir(parents=True,exist_ok=True);n=len(meta['products'][product]['cells']);dates=pd.date_range('2025-12-01',latest);values=np.full((len(dates),n),np.nan,np.float32)
 if product=='mur':
  for j in jobs:
   z=np.load(j['path']);assert z['dates'].tolist()==dates.strftime('%Y-%m-%d').tolist();values[:,z['take']]=z['values']
 else:
  for i,date in enumerate(dates):
   with Dataset(ROOT/'downloads'/f'oisst_{date:%Y%m%d}.nc') as d:
    lat=np.array(d['lat'][:]);lon=np.array(d['lon'][:]);v=np.ma.filled(d['sst'][0,0],np.nan);cells=np.array(meta['products']['oisst']['cells']);y=np.abs(lat[:,None]-cells[:,1]).argmin(0);x=np.abs(lon[:,None]-cells[:,0]).argmin(0);values[i]=v[y,x]
    assert abs(lat[y]-cells[:,1]).max()<.001 and abs(lon[x]-cells[:,0]).max()<.001
 assert np.isfinite(values).all()
 clim=np.load(ROOT/'baseline'/f'{product}_clim.npy',mmap_mode='r');threshold=np.load(ROOT/'baseline'/f'{product}_threshold.npy',mmap_mode='r');doy=dates.dayofyear.to_numpy()-1;mask=np.zeros_like(values,bool)
 for basin,(a,b) in meta['products'][product]['basinCellRanges'].items():mask[:,a:b]=mask_for(values[:,a:b]>threshold[doy,a:b],basin=='eastasia')
 keep=dates.year==2026;ds=dates[keep];sst=values[keep];m=mask[keep];exc=sst-threshold[doy[keep]];an=sst-clim[doy[keep]];days=m.sum(0);starts=m&~np.vstack([np.zeros((1,n),bool),m[:-1]]);freq=starts.sum(0);cumulative=np.where(m,exc,0).sum(0);metrics=np.column_stack([days,freq,np.divide(days,freq,out=np.full(n,np.nan),where=freq>0),np.divide(cumulative,days,out=np.full(n,np.nan),where=days>0),np.nanmax(np.where(m,exc,np.nan),axis=0),cumulative]).astype('<f4')
 # Cell-major arrays support range-free small perpoint loads from a static site.
 chunk=256;files=[]
 for a in range(0,n,chunk):
  b=min(a+chunk,n);sub=out/f'{a//chunk:04d}';sub.mkdir(exist_ok=True)
  for name,data,dtype in [('sst',sst[:,a:b],'<i2'),('anomaly',an[:,a:b],'<i2'),('intensity',exc[:,a:b],'<i2'),('mhw',m[:,a:b],'u1')]:
   arr=np.round(data*100).astype(dtype) if name!='mhw' else data.astype(dtype);p=sub/f'{name}.bin.gz';p.write_bytes(gzip.compress(arr.T.tobytes(),compresslevel=6,mtime=0));files.append(p)
 months=[];monthly=[]
 for mo in range(1,ds.month.max()+1):months.append(f'2026-{mo:02d}');monthly.append(m[ds.month==mo].sum(0))
 (out/'monthly_mhw_days.bin.gz').write_bytes(gzip.compress(np.array(monthly,dtype='u1').T.tobytes(),mtime=0));(out/'metrics_to_date.f32.gz').write_bytes(gzip.compress(metrics.tobytes(),mtime=0))
 # Last four days can acquire event membership as later observations arrive.
 write_json(out/'index.json',{'product':product,'nativeCells':n,'dateStart':'2026-01-01','dateEnd':latest,'dates':ds.strftime('%Y-%m-%d').tolist(),'monthDates':months,'chunkSize':chunk,'layout':'cell-major, then date; chunk index floor(nativeCell/256), row nativeCell%256','arrays':{'sst':'int16 hundredths C','anomaly':'int16 hundredths C vs fixed climatology','intensity':'int16 hundredths C vs fixed 90th percentile','mhw':'uint8 observed event membership'},'compression':'gzip','binarySuffix':'.bin.gz','monthlyFile':'monthly_mhw_days.bin.gz','metricsFile':'metrics_to_date.f32.gz','monthly':'monthly_mhw_days.bin.gz cell-major uint8','metrics':'metrics_to_date.f32.gz cell-major float32','metricSemantics':'2026-to-date segments, with frequency reset on 1 January and mean duration equal to within-2026 event days divided by within-2026 segments; ongoing events remain provisional','metricOrder':METRICS,'yearComplete':False,'trailingEventCheckDays':6,'trailingEventCheckDaysByBasin':{'redsea':4,'gulf':4,'eastasia':6},'basinCellRanges':meta['products'][product]['basinCellRanges'],'baselines':{'mur':'2003-2022','oisst':'1982-2011'},'eventRules':{'redsea':'at least five consecutive days above p90','gulf':'at least five consecutive days above p90','eastasia':'gaps of up to two days joined before the five-day minimum event filter, matching the archived source mask'},'source': 'NASA/JPL MUR v4.1 via NOAA ERDDAP' if product=='mur' else 'NOAA OISST v2.1 final and preliminary daily NCEI files','sourceURL':'https://coastwatch.pfeg.noaa.gov/erddap/info/jplMURSST41/index.html' if product=='mur' else 'https://www.ncei.noaa.gov/products/optimum-interpolation-sst','preliminaryDates':[] if product=='mur' else [str(d.date()) for d in ds if json.loads((ROOT/'downloads'/f'oisst_{d:%Y%m%d}.source.json').read_text())['preliminary']],'downloadedAt':stamp()})
 manifest={str(p.relative_to(ROOT/'public')):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file()};write_json(out/'checksums.json',manifest)
 progress(product,status='complete',latestDate=latest,message='2026 observed history computed and checked; incomplete year kept separate',analysisComplete=True)
 emit_manifest(meta,{product:latest,**{p:r['latestDate'] for p,r in STATUS['products'].items()}})

def emit_manifest(meta,latest):
 ready={p:{'index':p+'/index.json','latestDate':latest[p]} for p in latest if (ROOT/'public'/p/'index.json').exists()};files={str(p.relative_to(ROOT/'public')):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in (ROOT/'public').rglob('*') if p.is_file() and p.name!='manifest.json'}
 write_json(ROOT/'public'/'manifest.json',{'updatedAt':stamp(),'year':2026,'yearComplete':False,'products':ready,'allProductsComplete':len(ready)==len(latest),'historicalArraysChanged':False,'independentQCComplete':True,'files':files,'baselineValidation':{p:json.loads((ROOT/'baseline'/f'{p}_validation.json').read_text()) for p in ready}})

def main():
 global ROOT,STATUS,META
 a=argparse.ArgumentParser();a.add_argument('--root',type=Path,required=True);args=a.parse_args();ROOT=args.root.resolve();ROOT.mkdir(parents=True,exist_ok=True);(ROOT/'downloads').mkdir(exist_ok=True);META=json.loads((ROOT/'metadata.json').read_text());latest={'mur':'2026-10-20','oisst':'2026-10-20'}
 STATUS={'status':'running','startedAt':stamp(),'basins':['redsea','gulf','eastasia'],'products':{p:{'status':'queued','latestDate':latest[p],'completed':0,'total':0,'rate':0,'error':None,'nativeCells':len(META['products'][p]['cells'])} for p in latest},'message':'Downloading 2026 habitat-cell observations; original 1982/2003-2025 archives remain unchanged'};status()
 mur=mur_jobs(META,latest['mur']);oisst=[{'name':f'oisst_{d:%Y%m%d}','product':'oisst','date':f'{d:%Y-%m-%d}','path':ROOT/'downloads'/f'oisst_{d:%Y%m%d}.nc'} for d in pd.date_range('2025-12-01',latest['oisst'])];alljobs=oisst+mur
 totals={'mur':len(mur),'oisst':len(oisst)};done={p:sum(j['path'].exists() for j in alljobs if j['product']==p) for p in latest};cached=done.copy();start=time.time()
 for p in latest:
  ready=ROOT/'public'/p/'index.json';published=ready.exists() and (ROOT/'public/manifest.json').exists() and json.loads(ready.read_text()).get('dateEnd')==latest[p]
  progress(p,status='complete' if published else ('downloaded' if done[p]==totals[p] else 'downloading'),completed=done[p],total=totals[p],cachedFiles=cached[p],analysisComplete=published)
 def job(j):
  if j['product']=='mur':download_mur(j,latest['mur'])
  else:download_oisst(j,latest['oisst'])
  with LOCK:
   done[j['product']]+=1
   rec=STATUS['products'][j['product']];rec.update(completed=done[j['product']],rate=round((done[j['product']]-cached[j['product']])/max((time.time()-start)/60,1e-9),2),status='downloaded' if done[j['product']]==totals[j['product']] else 'downloading');STATUS['updatedAt']=stamp();STATUS['jobs']=[dict(name=p,product=p,basin='all',stage=r.get('status'),**r) for p,r in STATUS.get('products',{}).items()];write_json(ROOT/'status.json',STATUS)
 pending=[j for j in alljobs if not j['path'].exists()]
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
  future={executor.submit(job,j):j for j in pending}
  # Baseline I/O is local to the server, while both polite NOAA download slots run.
  for p in ['oisst','mur']:
   baseline(META,p)
  validate_old_oisst()
  errors=[]
  for f in concurrent.futures.as_completed(future):
   j=future[f]
   try:f.result()
   except Exception as ex:errors.append({'job':j['name'],'error':str(ex),'retryable':isinstance(ex,requests.exceptions.RequestException)});progress(j['product'],error=str(ex),status='retry needed');print('DOWNLOAD ERROR',j['name'],repr(ex),flush=True)
   if j['product']=='oisst' and done['oisst']==totals['oisst'] and not STATUS['products']['oisst'].get('analysisComplete'):analyse(META,'oisst',latest['oisst'],oisst)
  if errors:
   write_json(ROOT/'errors.json',errors)
   if all(e['retryable'] for e in errors):raise RuntimeError(f'{len(errors)} downloads need retry; run same command to resume')
   raise ValueError('Downloaded data failed validation; review errors.json before resuming')
 for p,jobs in [('oisst',oisst),('mur',mur)]:
  if not STATUS['products'][p].get('analysisComplete'):analyse(META,p,latest[p],jobs)
 emit_manifest(META,latest);status(status='complete',message='2026 observed heatwave history ready for all three study areas')
OISST_LOCK=threading.Lock()
if __name__=='__main__':
 try:main()
 except Exception as ex:
  if ROOT:status(status='retrying' if 'downloads need retry' in str(ex) else 'failed',retryable='downloads need retry' in str(ex),error=str(ex),traceback=traceback.format_exc());print(traceback.format_exc(),flush=True)
  raise
