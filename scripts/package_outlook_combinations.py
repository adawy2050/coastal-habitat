"""Serve point-sized forecast comparison records, retaining full arrays locally."""
from pathlib import Path
import gzip,json,shutil
import numpy as np
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'dist/forecasts/combinations'

def main():
    for product in ['oisst','mur']:
        folder=OUT/product;j=json.loads((folder/'summary.json').read_text())
        n=j['nativeCells'];nt=len(j['testYears']);nc=len(j['candidates'])
        raw=ROOT/'_cache/outlook_combinations'/product;raw.mkdir(parents=True,exist_ok=True)
        # Move only this script's enumerated generated arrays, never source observations.
        for name in j.get('files',[p.stem for p in raw.glob('*.f32')]):
            source=folder/f'{name}.f32'
            if source.exists():shutil.move(str(source),str(raw/source.name))
        read=lambda name:np.fromfile(raw/f'{name}.f32',dtype='<f4')
        fields=[];values=[]
        for name in ['candidate_probability','candidate_skill','candidate_brier']:
            a=read(name).reshape(nc,n).T
            fields.extend(f'{name}:{c["id"]}' for c in j['candidates']);values.append(a)
        a=read('candidate_backtest').reshape(nc,nt,n).transpose(2,0,1).reshape(n,nc*nt)
        fields.extend(f'backtest:{c["id"]}:{year}' for c in j['candidates'] for year in j['testYears']);values.append(a)
        for name in ['truth','policy_backtest']:
            values.append(read(name).reshape(nt,n).T);fields.extend(f'{name}:{year}' for year in j['testYears'])
        for name in ['policy_probability','policy_skill','selected_candidate','threshold','gain_lower','gain_upper','sst_source','sst_distance_km']:
            values.append(read(name)[:,None]);fields.append(name)
        matrix=np.concatenate(values,axis=1).astype('<f4');chunk=256
        for start in range(0,n,chunk):
            (folder/f'points_{start//chunk}.f32.gz').write_bytes(gzip.compress(matrix[start:start+chunk].tobytes(),compresslevel=6,mtime=0))
        j.update(fields=fields,chunkCells=chunk,pointFilePattern=f'{product}/points_{{chunk}}.f32.gz',pointLayout='cell-major, then fields; gzip little-endian float32')
        j.pop('files',None)
        (folder/'summary.json').write_text(json.dumps(j,indent=2),encoding='utf-8')
        print(product,n,'packed point records',matrix.shape[1],'fields',flush=True)

if __name__=='__main__':main()
