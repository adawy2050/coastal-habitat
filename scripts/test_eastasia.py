"""Independent preservation, attachment and source-day checks for the extension."""
from pathlib import Path
import json
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'dist/data';BASE=ROOT/'_cache/pre_eastasia/data';EAST=ROOT/'_cache/eastasia_export'
def main():
    meta=json.loads((DATA/'metadata.json').read_text());old=json.loads((BASE/'metadata.json').read_text());pixels=json.loads((DATA/'pixels.json').read_text())['rows'];previous=json.loads((BASE/'pixels.json').read_text())['rows'];assert pixels[:len(previous)]==previous
    assert meta['pixels']==210680 and meta['habitatRecords']==230128
    assert len(pixels)==len({(p[0],p[1]) for p in pixels})
    sites=pd.read_csv(EAST/'sites.csv');records=[]
    for product in ['mur','oisst']:
        nr=len(old['products'][product]['cells']);n=len(meta['products'][product]['cells']);ny=len(meta['products'][product]['years'])
        assert meta['products'][product]['cells'][:nr]==old['products'][product]['cells']
        for name in meta['metrics']+['season_MAM','season_JJA','season_SON','season_DJF']+(['sst'] if product=='oisst' else []):
            a=np.fromfile(DATA/f'{product}_{name}.f32',dtype='<f4').reshape(ny,n);b=np.fromfile(BASE/f'{product}_{name}.f32',dtype='<f4').reshape(ny,nr);assert np.array_equal(a[:,:nr],b,equal_nan=True),(product,name)
            if not name.startswith('season_'):
                source=np.fromfile(EAST/f'{product}_{name}.f32',dtype='<f4').reshape(ny,n-nr);assert np.array_equal(a[:,nr:],source,equal_nan=True)
        for path in BASE.glob(f'{product}_outlook_*.f32'):
            before=np.fromfile(path,dtype='<f4');after=np.fromfile(DATA/path.name,dtype='<f4')
            if 'coefficients' in path.name:after=after.reshape(n,7)[:nr].ravel()
            elif 'backtest' in path.name:after=after.reshape(-1,n)[:,:nr].ravel()
            else:after=after[:nr]
            assert np.array_equal(after,before,equal_nan=True),path.name
        # Compare annual days with the saved, original site-overlay result at
        # locations that keep exactly the original marine source cell.
        attachment=np.load(EAST/f'{product}_attachment.npz');index=attachment['index'];cells=attachment['cells'];source_lon=cells[index,0];source_lat=cells[index,1]
        if product=='mur':same=(abs(source_lon-sites.lon.to_numpy())<.0001)&(abs(source_lat-sites.lat.to_numpy())<.0001)
        else:
            original_lon=100.125+np.rint((sites.lon.to_numpy()-100.125)/.25)*.25;original_lat=.125+np.rint((sites.lat.to_numpy()-.125)/.25)*.25;same=(abs(original_lon-source_lon)<.0001)&(abs(original_lat-source_lat)<.0001)
        rng=np.random.default_rng(739);take=rng.choice(np.flatnonzero(same),min(180,int(same.sum())),replace=False)
        targets=pd.read_csv(Path(r'D:\heatwaveseastasia\data\derived\existing_results_site_overlay_20260402\target_meta.csv'),usecols=['target_id','grid_site_id']);lookup=targets.set_index('grid_site_id').target_id;selected=dict(zip(lookup.loc[sites.grid_site_id.iloc[take]],index[take]));years=meta['products'][product]['years'];annual=np.fromfile(DATA/f'{product}_mhw_days.f32',dtype='<f4').reshape(ny,n)[:,nr:];count=0;difference=0.
        path=Path(r'D:\heatwaveseastasia\data\derived\existing_results_site_overlay_20260402')/f"site_metrics_{'ghrsst' if product=='mur' else product}.csv.gz"
        for chunk in pd.read_csv(path,usecols=['target_id','year','mhw_days'],chunksize=400000):
            part=chunk[chunk.target_id.isin(selected)]
            for row in part.itertuples(index=False):
                diff=abs(annual[years.index(row.year),selected[row.target_id]]-row.mhw_days);difference=max(difference,float(diff));count+=1
        assert count>=180*ny and difference<.0001,(product,count,difference)
        records.append({'product':product,'originalSiteAnnualDayComparisons':count,'maxDifference':difference,'previousAnnualSeasonalAndForecastValuesUnchanged':True})
    result={'passed':True,'checks':records,'retainedEastAsiaCells':len(sites),'totalCells':len(pixels)};(ROOT/'qa/eastasia_data_results.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
