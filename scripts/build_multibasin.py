"""Combine independently extracted Gulf pixels with the verified Red Sea atlas.

Requires _cache/redsea_atlas_base (the original Red Sea display package) and
_cache/gulf_extracted (output of extract_gulf_remote.py). Source studies stay intact.
"""
from pathlib import Path
import copy
import hashlib
import json
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'dist/data'
BASE=ROOT/'_cache/redsea_atlas_base'
GULF=ROOT/'_cache/gulf_extracted'


def write(name,value):
    (DATA/name).write_text(json.dumps(value,separators=(',',':'),allow_nan=False),encoding='utf-8')


def main():
    red=json.loads((BASE/'metadata.json').read_text())
    gulf=json.loads((GULF/'metadata.json').read_text())
    meta=copy.deepcopy(red)
    meta['regions']=red['regions']+gulf['regions']
    meta['basins']=[{'id':'redsea','name':'Red Sea & Gulf of Aden','regions':[0,1,2],'bounds':[[9.5,31],[30,52.5]],'pixels':red['pixels'],'habitatRecords':red['habitatRecords']},
                    {'id':'gulf','name':'Arabian Gulf & Gulf of Oman','regions':[3,4],'bounds':[[22,47],[31.5,60]],'pixels':gulf['pixels'],'habitatRecords':gulf['habitatRecords']}]
    meta['pixels']=red['pixels']+gulf['pixels'];meta['habitatRecords']=red['habitatRecords']+gulf['habitatRecords']
    meta['bounds']=[[9.5,31],[31.5,60]]
    meta['source']='Independent Red Sea corrected attachments and Arabian Gulf native annual/event outputs; unique habitat-cell sampling; no new MHW detection'
    old=json.loads((BASE/'pixels.json').read_text());added=json.loads((GULF/'pixels.json').read_text())['rows']
    for row in added:
        row[3]+=len(red['regions']);row[4]+=len(red['products']['mur']['cells']);row[5]+=len(red['products']['oisst']['cells'])
    points=old['rows']+added
    write('pixels.json',{'columns':old['columns'],'rows':points})
    checks=[]
    for product in ['mur','oisst']:
        r,g=red['products'][product],gulf['products'][product]
        assert r['years']==g['years'] and r['baseline']==g['baseline']
        nr,ng=len(r['cells']),len(g['cells']);ny=len(r['years'])
        meta['products'][product]['cells']=r['cells']+g['cells']
        meta['products'][product]['basinCellRanges']={'redsea':[0,nr],'gulf':[nr,nr+ng]}
        names=meta['metrics']+[f'season_{s}' for s in ['MAM','JJA','SON','DJF']]+(['sst'] if product=='oisst' else [])
        for metric in names:
            name=f'{product}_{metric}.f32'
            a=np.fromfile(BASE/name,dtype='<f4').reshape(ny,nr);b=np.fromfile(GULF/name,dtype='<f4').reshape(ny,ng)
            merged=np.concatenate([a,b],axis=1)
            assert np.array_equal(merged[:,:nr],a,equal_nan=True)
            merged.astype('<f4').tofile(DATA/name)
        checks.append({'product':product,'redSeaNativeCells':nr,'gulfNativeCells':ng,'redSeaValuesUnchanged':True})
    write('metadata.json',meta)
    # Build only habitat/region combinations actually present in each basin.
    p=np.array(points)
    groups=[]
    for basin in meta['basins']:
        for h in meta['habitats']:groups.append({'scope':'overall','habitat':h,'region':basin['name'],'basin':basin['id']})
        for region in basin['regions']:
            for k,h in enumerate(meta['habitats']):
                if np.any((p[:,3]==region)&((p[:,2].astype(int)&(1<<k))!=0)):
                    groups.append({'scope':'ecoregion','habitat':h,'region':meta['regions'][region],'basin':basin['id']})
    grouped={'groups':groups,'products':{}}
    weights={}
    for product in ['mur','oisst']:
        n=len(meta['products'][product]['cells']);vectors=[]
        for group in groups:
            keep=(p[:,2].astype(int)&(1<<meta['habitats'].index(group['habitat'])))!=0
            basin=next(b for b in meta['basins'] if b['id']==group['basin'])
            keep&=np.isin(p[:,3],basin['regions'])
            if group['scope']=='ecoregion':keep&=p[:,3]==meta['regions'].index(group['region'])
            assert keep.any()
            vectors.append(np.bincount(p[keep,4 if product=='mur' else 5].astype(int),minlength=n)/keep.sum())
        weights[product]=np.array(vectors).T
        years=meta['products'][product]['years'];seasons={}
        for season in ['MAM','JJA','SON','DJF']:
            a=np.fromfile(DATA/f'{product}_season_{season}.f32',dtype='<f4').reshape(len(years),n)
            # Last DJF is wholly missing; avoid spreading NaNs from absent cells.
            a=a@weights[product]
            seasons[season]=[[None if not np.isfinite(v) else float(v) for v in row] for row in a]
        grouped['products'][product]={'years':years,'seasons':seasons}
    write('seasonal_groups.json',grouped)
    original=pd.read_csv(BASE/'seasonal_training.csv');parts=[original.copy()]
    for group_index,group in enumerate(groups):
        if group['scope']!='ecoregion' or group['basin']=='redsea':continue
        for product in ['mur','oisst']:
            name=meta['products'][product]['name']
            template=original[(original['product']==name)&(original.habitat=='coral')&(original.region=='Gulf of Aden')].copy()
            template['habitat']=group['habitat'];template['region']=group['region']
            years=np.array(grouped['products'][product]['years'])
            for season in ['MAM','JJA','SON','DJF']:
                select=template.season==season;positions=np.searchsorted(years,template.loc[select,'season_start_year'])
                outcomes=np.array(grouped['products'][product]['seasons'][season],dtype=float)
                template.loc[select,'observed_mhw_days']=outcomes[positions,group_index]
            assert template.observed_mhw_days.notna().all();parts.append(template)
    pd.concat(parts,ignore_index=True).to_csv(DATA/'seasonal_training.csv',index=False)
    # The original Red Sea annual-summary validation stays as a named audit.
    validation=json.loads((BASE/'validation.json').read_text())
    raw_checks=[];dedup_checks=[]
    metrics=meta['metrics']
    for product,suffix in [('mur','ghrsst'),('oisst','oisst')]:
        source=ROOT/'_cache/gulf_source'/f'site_annual_mhw_{suffix}.parquet'
        frame=pd.read_parquet(source)
        assert (frame.groupby(['grid_site_id','year'])[metrics].nunique(dropna=False).to_numpy()<=1).all()
        reference=pd.read_csv(ROOT/'_cache/gulf_source'/('habitat_meow_year_summary.csv' if product=='mur' else 'habitat_meow_year_summary_oisst.csv'))
        means=frame.groupby(['year','habitat_group','meow_ecoregion'])[metrics].mean().reset_index().merge(reference,on=['year','habitat_group','meow_ecoregion'],suffixes=('_data','_ref'))
        for metric in metrics:
            diff=float(np.nanmax(abs(means[metric+'_data']-means[metric+'_ref'])))
            assert diff<.00015;raw_checks.append({'product':product,'metric':metric,'originalSummaryMaxDifference':diff})
        dedup_checks.append({'product':product,'duplicateAnnualRowsRemoved':int(frame.duplicated(['grid_site_id','habitat_group','year']).sum()),'contradictoryAnnualValues':False})
    write('gulf_validation.json',{'sourceAnnualSummaryChecks':raw_checks,'duplicateChecks':dedup_checks,'nativeSeasonalChecks':gulf['checks'],
        'attachmentAudit':{k:v for k,v in gulf.items() if k not in ['products','regions','checks']},'mergeChecks':checks,
        'allChecksPassed':True,'sourceCompleteness':json.loads((ROOT/'_cache/gulf_source/remote_validation.json').read_text()),'sourceHashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'_cache/gulf_source').glob('*') if p.is_file()}})
    validation['gulfValidation']='gulf_validation.json';validation['pixelCount']=meta['pixels'];validation['recordCount']=meta['habitatRecords'];validation['redSeaPixelCount']=red['pixels']
    write('validation.json',validation)
    print('COMBINED ATLAS READY',meta['pixels'],'unique habitat cells;',len(groups),'habitat/basin/ecoregion groups',flush=True)


if __name__=='__main__':main()
