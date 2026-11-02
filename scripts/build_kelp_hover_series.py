"""Compact native annual individual-mass histories for immediate hover plots."""
from pathlib import Path
import gzip,json,struct
import numpy as np
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'dist/kelp/data'
c=json.loads((D/'catalogue.json').read_text(encoding='utf-8'));out={}
for s in c['stations']:
 raw=gzip.decompress((D/s['files']['historical']).read_bytes());m,y,f,a=struct.unpack_from('<4I',raw);scales=np.frombuffer(raw,dtype='<f8',count=f+a,offset=16);q=np.frombuffer(raw,dtype='<u2',offset=16+8*(f+a));idx=c['annualFields'].index('mass');v=q[m*f:].reshape(y,a)[:,idx];first=int(c['species'][s['species']]['scenarios']['historical']['firstMonth'][:4]);out[s['id']]={'years':list(range(first,first+y)),'mass':[round(float(n*scales[f+idx]),5) if n!=65535 else None for n in v]}
(D/'hover-mass.json.gz').write_bytes(gzip.compress(json.dumps(out,separators=(',',':')).encode(),mtime=0));print('Annual hover histories:',len(out))
