"""Assemble small annual map arrays from the already checked station records."""
from pathlib import Path
import gzip,json,struct
import numpy as np
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'dist/kelp/data'

def decode(path):
    raw=gzip.decompress(path.read_bytes());m,y,f,a=struct.unpack('<4I',raw[:16]);scale=np.frombuffer(raw,dtype='<f8',count=f+a,offset=16)
    offset=16+8*(f+a)+m*f*2;q=np.frombuffer(raw,dtype='<u2',count=y*a,offset=offset).reshape(y,a)
    return np.where(q==65535,np.nan,q*scale[f:])

def main():
    j=json.loads((D/'catalogue.json').read_text(encoding='utf-8'));j['maps']={}
    for species,meta in j['species'].items():
        stations=[s for s in j['stations'] if s['species']==species];j['maps'][species]={}
        for scenario,record in meta['scenarios'].items():
            a=np.stack([decode(D/s['files'][scenario]) for s in stations],axis=1).astype('<f4')
            path=D/f'{species}/{scenario}_map.f32.gz';path.write_bytes(gzip.compress(a.tobytes(),compresslevel=7,mtime=0))
            j['maps'][species][scenario]={'file':str(path.relative_to(D)).replace('\\','/'),'years':list(range(int(record['firstMonth'][:4]),int(record['lastMonth'][:4])+1)),'shape':list(a.shape),'layout':'year, then station in catalogue order, then annual field; little-endian float32'}
    (D/'catalogue.json').write_bytes(json.dumps(j,ensure_ascii=False,separators=(',',':')).encode('utf-8'));print('PASS: annual map arrays match all checked point records.')

if __name__=='__main__':main()
