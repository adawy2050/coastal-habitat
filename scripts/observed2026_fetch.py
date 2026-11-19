"""Fetch only validated observed-2026 exports; verify every file and daily/monthly sums."""
from pathlib import Path
import argparse,gzip,hashlib,io,json,shlex,tarfile
import numpy as np
from observed2026_sync import connection,ROOT,REMOTE

def verify(root):
 manifest=json.loads((root/'manifest.json').read_text());assert manifest['independentQCComplete'] and not manifest['historicalArraysChanged']
 for name,entry in manifest['files'].items():
  p=root/name;assert p.stat().st_size==entry['bytes'],name;assert hashlib.sha256(p.read_bytes()).hexdigest()==entry['sha256'],name
 results=[]
 for product in manifest['products']:
  d=root/product;j=json.loads((d/'index.json').read_text());n=j['nativeCells'];nd=len(j['dates']);nm=len(j['monthDates']);chunk=j['chunkSize'];monthly=np.frombuffer(gzip.decompress((d/j['monthlyFile']).read_bytes()),dtype='u1').reshape(n,nm);metrics=np.frombuffer(gzip.decompress((d/j['metricsFile']).read_bytes()),dtype='<f4').reshape(n,6);months=np.array([int(x[5:7]) for x in j['dates']]);checked=0
  for a in range(0,n,chunk):
   b=min(a+chunk,n);sub=d/f'{a//chunk:04d}';arrays={name:np.frombuffer(gzip.decompress((sub/f'{name}.bin.gz').read_bytes()),dtype='u1' if name=='mhw' else '<i2').reshape(b-a,nd) for name in ['sst','anomaly','intensity','mhw']};mask=arrays['mhw'];assert np.isin(mask,[0,1]).all();assert np.array_equal(mask.sum(1),metrics[a:b,0]);assert np.array_equal(monthly[a:b].sum(1),metrics[a:b,0]);assert arrays['sst'].min()>=-300 and arrays['sst'].max()<=4500
   for m in range(1,nm+1):assert np.array_equal(mask[:,months==m].sum(1),monthly[a:b,m-1])
   event=mask.astype(bool);frequency=(event&~np.column_stack([np.zeros(b-a,bool),event[:,:-1]])).sum(1);assert np.array_equal(frequency,metrics[a:b,1]);days=event.sum(1);has=days>0;assert np.allclose(metrics[a:b,2][has],days[has]/frequency[has]);assert np.allclose(metrics[a:b,3][has],metrics[a:b,5][has]/days[has]);quantizedCumulative=np.where(event,arrays['intensity']*.01,0).sum(1);assert np.all(abs(quantizedCumulative-metrics[a:b,5])<=days*.0051+.01)
   if has.any():quantizedMax=np.max(np.where(event[has],arrays['intensity'][has]*.01,-np.inf),axis=1);assert np.all(abs(quantizedMax-metrics[a:b,4][has])<=.0051)
   checked+=b-a
  results.append({'product':product,'nativeCells':checked,'dateStart':j['dateStart'],'dateEnd':j['dateEnd'],'monthlyDailyMetricDaysExact':True,'allFileHashesMatch':True,'allSixMetricsReproducedWithinExportPrecision':True})
 return {'products':results,'independentSourceChecks':manifest['baselineValidation'],'complete':True}

def main():
 a=argparse.ArgumentParser();a.add_argument('--verify-only',action='store_true');args=a.parse_args();out=ROOT/'dist/observed2026';out.mkdir(parents=True,exist_ok=True)
 if not args.verify_only:
  c=connection()
  f=c.open_sftp();f.put(str(ROOT/'scripts/observed2026_boundary_remote.py'),REMOTE+'/boundary.py');f.close()
  _,stdout,stderr=c.exec_command('cd '+shlex.quote(REMOTE)+' && python boundary.py --root '+shlex.quote(REMOTE),timeout=300)
  message=stdout.read().decode();error=stderr.read().decode();assert stdout.channel.recv_exit_status()==0,error
  print(message.strip(),flush=True)
  code=f'''from pathlib import Path
import hashlib,io,json,tarfile
root=Path({REMOTE!r})/'public';manifest=json.loads((root/'manifest.json').read_text());data=json.dumps(manifest,ensure_ascii=False,separators=(',',':')).encode()
assert manifest['independentQCComplete']
with tarfile.open(root.parent/'ready_export.tar','w') as tar:
 for name,entry in manifest['files'].items():
  p=root/name;assert hashlib.sha256(p.read_bytes()).hexdigest()==entry['sha256'],name;tar.add(p,arcname=name)
 info=tarfile.TarInfo('manifest.json');info.size=len(data);tar.addfile(info,io.BytesIO(data))
print(hashlib.sha256((root.parent/'ready_export.tar').read_bytes()).hexdigest())
'''
  _,stdout,stderr=c.exec_command('python -c '+shlex.quote(code),timeout=300);digest=stdout.read().decode().strip();error=stderr.read().decode();assert len(digest)==64,error
  cache=ROOT/'_cache/observed2026';cache.mkdir(parents=True,exist_ok=True);archive=cache/'ready_export.tar';f=c.open_sftp();f.get(REMOTE+'/ready_export.tar',str(archive));f.close();c.close();assert hashlib.sha256(archive.read_bytes()).hexdigest()==digest
  with tarfile.open(archive) as tar:tar.extractall(out,filter='data')
 result=verify(out);qa=ROOT/'qa/observed2026_validation.json';qa.parent.mkdir(exist_ok=True);qa.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
