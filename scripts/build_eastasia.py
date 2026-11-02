"""Append independently extracted East Asia cells; verify earlier numbers unchanged."""
from pathlib import Path
import copy,hashlib,json,shutil
import numpy as np,pandas as pd

ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'dist/data';BASE=ROOT/'_cache/pre_eastasia';EAST=ROOT/'_cache/eastasia_export';SOURCE=Path(r'D:\heatwaveseastasia')
def write(path,value):path.write_text(json.dumps(value,separators=(',',':'),allow_nan=False),encoding='utf8',newline='\n')
def main():
    if not BASE.exists():
        assert not any(b['id']=='eastasia' for b in json.loads((DATA/'metadata.json').read_text()).get('basins',[])), 'Restore the pre-East-Asia baseline (commit 9916b25) into _cache/pre_eastasia before rebuilding.'
        shutil.copytree(DATA,BASE/'data');shutil.copytree(ROOT/'dist/detail/monthly',BASE/'monthly')
    base=BASE/'data';meta=json.loads((base/'metadata.json').read_text());oldmeta=copy.deepcopy(meta);old=json.loads((base/'pixels.json').read_text());sites=pd.read_csv(EAST/'sites.csv');sites['meow_ecoregion']=sites.meow_ecoregion.fillna('Unassigned ecoregion');membership=pd.read_parquet(SOURCE/'data/derived/revised_habitat_20260402/grid_site_habitat_membership_ghrsst.parquet').drop_duplicates(['grid_site_id','habitat_group'])
    habitats=meta['habitats']+['kelp_macroalgae'];bits=membership.assign(bit=membership.habitat_group.map(dict(zip(habitats,[1,2,4,8])))).groupby('grid_site_id').bit.sum();regions=sorted(sites.meow_ecoregion.unique());region_offset=len(meta['regions']);meta['regions']+=regions;meta['habitats']=habitats
    att={p:{k:z[k] for k in z.files} for p in ['mur','oisst'] for z in [np.load(EAST/f'{p}_attachment.npz')]};offset={p:len(meta['products'][p]['cells']) for p in att}
    added=[[round(float(s.lon),2),round(float(s.lat),2),int(bits[s.grid_site_id]),region_offset+regions.index(s.meow_ecoregion),int(att['mur']['index'][i])+offset['mur'],int(att['oisst']['index'][i])+offset['oisst'],round(float(att['mur']['distance'][i]),3),round(float(att['oisst']['distance'][i]),3),int(s.lat_idx),int(s.lon_idx)] for i,s in enumerate(sites.itertuples(index=False))]
    print('Mapped East Asia habitat cells',len(added),flush=True);points=old['rows']+added;pixels=np.array(points);meta['pixels']=len(points);meta['habitatRecords']=sum(int(p[2]).bit_count() for p in points);meta['bounds']=[[0,31],[55,160]]
    meta['basins'].append({'id':'eastasia','name':'East Asia & western Pacific','regions':list(range(region_offset,len(meta['regions']))),'bounds':[[0,110],[55,160]],'pixels':len(added),'habitatRecords':sum(int(p[2]).bit_count() for p in added)})
    meta['source']='Independent habitat-cell studies: Red Sea, Arabian Gulf and East Asia; archived heatwave states and native SST records'
    checks=[];monthly_data={};monthly_index=json.loads((BASE/'monthly/index.json').read_text())
    for product in att:
        info=meta['products'][product];nold=offset[product];ny=len(info['years']);newcells=np.round(att[product]['cells'],5).tolist();nnew=len(newcells);info['cells']+=newcells;info['basinCellRanges']['eastasia']=[nold,nold+nnew]
        monthly=np.load(EAST/f'{product}_monthly.npy').reshape(ny,12,nnew);seasons={}
        for season,start in [('MAM',2),('JJA',5),('SON',8),('DJF',11)]:
            if start<11:a=monthly[:,start:start+3].sum(1).astype('<f4')
            else:a=np.full((ny,nnew),np.nan,dtype='<f4');a[:-1]=monthly[:-1,11].astype(int)+monthly[1:,0].astype(int)+monthly[1:,1].astype(int)
            seasons[season]=a
        for name in meta['metrics']+[f'season_{s}' for s in seasons]+(['sst'] if product=='oisst' else []):
            a=np.fromfile(base/f'{product}_{name}.f32',dtype='<f4').reshape(ny,nold)
            b=seasons[name[7:]] if name.startswith('season_') else np.fromfile(EAST/f'{product}_{name}.f32',dtype='<f4').reshape(ny,nnew)
            merged=np.concatenate([a,b],axis=1);assert np.array_equal(merged[:,:nold],a,equal_nan=True);merged.astype('<f4').tofile(DATA/f'{product}_{name}.f32')
            checks.append({'product':product,'metric':name,'previousCellsUnchanged':True})
        p=monthly_index['products'][product];original=np.concatenate([np.fromfile(BASE/'monthly'/f,dtype='uint8').reshape(-1,len(p['dates'])) for f in p['files']],axis=0).T
        combined=np.concatenate([original,monthly.reshape(ny*12,nnew)],axis=1);monthly_data[product]=combined;p['cells']=nold+nnew;p['files']=[]
        for start in range(0,p['cells'],monthly_index['chunkCells']):
            name=f"{product}_{start//monthly_index['chunkCells']}.u8";combined[:,start:start+monthly_index['chunkCells']].T.astype('uint8').tofile(ROOT/'dist/detail/monthly'/name);p['files'].append(name)
    print('Annual and monthly arrays merged',flush=True);write(DATA/'metadata.json',meta);write(DATA/'pixels.json',{'columns':old['columns'],'rows':points});write(ROOT/'dist/detail/monthly/index.json',monthly_index)
    # Daily SST remains at its native quarter-degree resolution.
    daily_archive=np.load(EAST/'oisst_daily.npz');daily={k:daily_archive[k] for k in daily_archive.files};target=ROOT/'dist/detail/daily/eastasia';target.mkdir(parents=True,exist_ok=True);dates=daily['dates'].tolist();files=[]
    for i in range(daily['values'].shape[1]):
        raw=daily['values'][:,i].astype('<i2').tobytes();name=f'{i}.i16';(target/name).write_bytes(raw);files.append({'file':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
    write(target/'index.json',{'source':'Original NOAA OISST v2.1 daily SST; East Asia archive, 100–180°E, 0–70°N','dates':dates,'period':[dates[0],dates[-1]],'encoding':'int16 little-endian, hundredths degree Celsius, -32768 missing','cells':att['oisst']['cells'].tolist(),'files':files})
    grouped=json.loads((base/'seasonal_groups.json').read_text());newgroups=[]
    for scope in ['overall','ecoregion']:
        for region in ([None] if scope=='overall' else range(region_offset,len(meta['regions']))):
            for k,h in enumerate(habitats):
                keep=(pixels[:,3]>=region_offset)&((pixels[:,2].astype(int)&(1<<k))!=0)
                if region is not None:keep&=pixels[:,3]==region
                if keep.any():newgroups.append({'scope':scope,'habitat':h,'region':'East Asia & western Pacific' if region is None else meta['regions'][region],'basin':'eastasia'})
    old_group_count=len(grouped['groups']);grouped['groups']+=newgroups
    for product in att:
        n=len(meta['products'][product]['cells']);years=meta['products'][product]['years'];weights=[]
        for group in newgroups:
            keep=(pixels[:,3]>=region_offset)&((pixels[:,2].astype(int)&(1<<habitats.index(group['habitat'])))!=0)
            if group['scope']=='ecoregion':keep&=pixels[:,3]==meta['regions'].index(group['region'])
            weights.append(np.bincount(pixels[keep,4 if product=='mur' else 5].astype(int),minlength=n)/keep.sum())
        weights=np.array(weights).T
        for season in ['MAM','JJA','SON','DJF']:
            a=np.fromfile(DATA/f'{product}_season_{season}.f32',dtype='<f4').reshape(len(years),n);valid=np.isfinite(a);sums=np.nan_to_num(a)@weights;denominator=valid.astype(float)@weights;v=np.divide(sums,denominator,out=np.full(sums.shape,np.nan),where=denominator>0)
            grouped['products'][product]['seasons'][season]=[oldrow+[float(x) if np.isfinite(x) else None for x in row] for oldrow,row in zip(grouped['products'][product]['seasons'][season],v)]
    write(DATA/'seasonal_groups.json',grouped)
    training=pd.read_csv(base/'seasonal_training.csv');parts=[training]
    for j,g in enumerate(newgroups,old_group_count):
        if g['scope']!='ecoregion':continue
        for product in att:
            template=training[(training['product']==meta['products'][product]['name'])&(training.habitat=='coral')&(training.region=='Gulf of Aden')].copy();template['habitat']=g['habitat'];template['region']=g['region'];years=np.array(meta['products'][product]['years'])
            for season in ['MAM','JJA','SON','DJF']:
                keep=template.season==season;positions=np.searchsorted(years,template.loc[keep,'season_start_year']);template.loc[keep,'observed_mhw_days']=np.array(grouped['products'][product]['seasons'][season],dtype=float)[positions,j]
            assert template.observed_mhw_days.notna().all();parts.append(template)
    pd.concat(parts,ignore_index=True).to_csv(DATA/'seasonal_training.csv',index=False)
    audit=json.loads((EAST/'validation.json').read_text());audit.update(mergeChecks=checks,habitatCells=len(added),habitatRecords=meta['basins'][-1]['habitatRecords'],regions=regions,allChecksPassed=True,intensityNote='Temperature intensity is reconstructed from saved anomaly + climatology - p90 threshold; the saved exceedance field is an integer flag, not degrees C.',previousMetadataSha256=hashlib.sha256((base/'metadata.json').read_bytes()).hexdigest())
    audit['intensityConvention']='Signed SST minus p90 over saved event masks, including joined gap days and calendar-year fragments; negative values retained.'
    for check in audit['checks']:check['intensityUnits']='Signed degrees C relative to saved p90 threshold'
    audit.pop('sourceRoots',None)
    audit['sourceRuns']={'mur':'BASIC_HOBDAY_t192_w8','oisst':'OISST_HOBDAY_1982_2025_BASE1982_2011'}
    write(DATA/'eastasia_validation.json',audit);validation=json.loads((base/'validation.json').read_text());validation.update(eastAsiaValidation='eastasia_validation.json',pixelCount=meta['pixels'],recordCount=meta['habitatRecords']);write(DATA/'validation.json',validation)
    print('EAST ASIA APPENDED',len(added),'cells;',len(regions),'ecoregions;',len(newgroups),'groups;',meta['pixels'],'total habitat cells')
if __name__=='__main__':main()
