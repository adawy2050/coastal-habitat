"""Compare completed 2026 months with the same months of earlier years.

Equal weights are retained habitat grid cells, including distinct habitat cells
that share a native SST source. Complete annual model inputs remain unchanged.
"""
from pathlib import Path
import calendar,csv,gzip,hashlib,json
import numpy as np

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'dist/observed2026'

def main():
    meta=json.loads((ROOT/'dist/data/metadata.json').read_text(encoding='utf8'));pixels=np.asarray(json.loads((ROOT/'dist/data/pixels.json').read_text(encoding='utf8'))['rows']);manifest=json.loads((OUT/'manifest.json').read_text(encoding='utf8'));old=json.loads((ROOT/'dist/detail/monthly/index.json').read_text(encoding='utf8'));summary={'products':{},'files':{}};records=[]
    for product in manifest['products']:
        index=json.loads((OUT/product/'index.json').read_text(encoding='utf8'));year,month,day=map(int,index['dateEnd'].split('-'));complete=month if day==calendar.monthrange(year,month)[1] else month-1;n=index['nativeCells'];ny=len(meta['products'][product]['years']);nm=len(index['monthDates'])
        if not complete:continue
        previous=np.concatenate([np.fromfile(ROOT/'dist/detail/monthly'/name,dtype='u1').reshape(-1,ny,12) for name in old['products'][product]['files']],axis=0);assert previous.shape==(n,ny,12)
        months=np.frombuffer(gzip.decompress((OUT/product/index['monthlyFile']).read_bytes()),dtype='u1').reshape(n,nm)
        comparison=np.column_stack([previous[:,:,:complete].sum(2),months[:,:complete].sum(1)]).astype('<u2');assert comparison.max()<=sum(calendar.monthrange(2026,m)[1] for m in range(1,complete+1))
        directory=OUT/product/'comparison';directory.mkdir(exist_ok=True);files=[]
        for start in range(0,n,256):
            path=directory/f'{start//256:04d}.u16.gz';path.write_bytes(gzip.compress(comparison[start:start+256].tobytes(),mtime=0));key=path.relative_to(OUT).as_posix();summary['files'][key]={'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()};files.append(key)
        years=meta['products'][product]['years']+[2026];summary['products'][product]={'years':years,'startMonth':1,'endMonth':complete,'endDate':f'2026-{complete:02d}-{calendar.monthrange(2026,complete)[1]}','chunkSize':256,'nativeCells':n,'dtype':'little-endian uint16','layout':'cell-major, then year','files':files,'description':'Observed heatwave days in the same completed calendar months of every year'}
        native=pixels[:,4 if product=='mur' else 5].astype(int)
        to_date=np.frombuffer(gzip.decompress((OUT/product/index['metricsFile']).read_bytes()),dtype='<f4').reshape(n,6)[:,0]
        for basin in meta['basins']:
            regional=np.isin(pixels[:,3].astype(int),basin['regions'])
            for region in [None,*basin['regions']]:
                area=regional if region is None else pixels[:,3].astype(int)==region
                for h,habitat in enumerate(meta['habitats']):
                    take=area&((pixels[:,2].astype(int)&(1<<h))!=0)
                    if not take.any():continue
                    cells=native[take];series=comparison[cells].mean(0);current=series[-1];rank=(np.sum(series[:-1]<current)+.5*np.sum(series[:-1]==current))/ny*100
                    records.append({'product':product,'basin':basin['id'],'ecoregion':'All retained regions' if region is None else meta['regions'][region],'habitat':habitat,'habitat_cells':len(cells),'native_sst_cells':len(np.unique(cells)),'date_start':'2026-01-01','date_end':index['dateEnd'],'mean_mhw_days_to_date':round(float(to_date[cells].mean()),4),'matched_months_end':complete,'matched_2026_mean_mhw_days':round(float(current),4),'historical_matched_mean_mhw_days':round(float(series[:-1].mean()),4),'historical_matched_percentile':round(float(rank),2),'reference_first_year':years[0],'reference_last_year':years[-2]})
        # Round-trip all native comparisons, independently of display code.
        restored=np.concatenate([np.frombuffer(gzip.decompress((OUT/name).read_bytes()),dtype='<u2').reshape(-1,len(years)) for name in files]);assert np.array_equal(restored,comparison)
        print(product,n,'native cells; completed months',complete,'comparison round-trip exact',flush=True)
    if records:
        path=OUT/'habitat_ecoregion_summary_2026.csv'
        with path.open('w',encoding='utf8',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
        summary['summaryCSV']=path.name
    with (OUT/'analysis.json').open('w',encoding='utf8',newline='\n') as stream:
        stream.write(json.dumps(summary,separators=(',',':')))

if __name__=='__main__':main()
