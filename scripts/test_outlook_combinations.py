"""Forward tests of local state, warming and alternative issued ENSO families.

Writes a separate comparison product. Does not replace the published outlook.
All fits are native-cell fits; local SST support is explicitly OISST. Fixed
ridge penalty 10 is declared before evaluation, avoiding another search layer.
"""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
from pathlib import Path
import argparse, gzip, json, time
import numpy as np
import pandas as pd
from scipy.special import expit
from scipy.spatial import cKDTree
from forecast_index_models import certified_2025

ROOT=Path(__file__).resolve().parents[1];D=ROOT/'dist/data'
OUT=ROOT/'dist/forecasts/combinations'
# Each feature list is fixed before any outcome scores are inspected.
SPECS=[('climatology','Historical frequency',[]),
 ('warming','Long-term change',['year']),
 ('local','Recent SST and heatwaves',['year','sst','mhw']),
 ('observed','Six observed indices',['observed']),
 ('local_observed','Local conditions + six observed indices',['year','sst','mhw','observed']),
 ('local_pacific','Local conditions + observed ENSO and PDO',['year','sst','mhw','pacific']),
 ('local_issued','Local conditions + issued ENSO mean',['year','sst','mhw','combined']),
 ('local_dynamic','Local conditions + dynamical ENSO',['year','sst','mhw','dynamic']),
 ('local_statistical','Local conditions + statistical ENSO',['year','sst','mhw','statistical']),
 ('local_both','Local conditions + both ENSO forecasts',['year','sst','mhw','dynamic','statistical']),
 ('local_all','Local conditions + observed indices + issued ENSO',['year','sst','mhw','observed','combined']),
 ('local_all_families','Local conditions + observed indices + both ENSO forecasts',['year','sst','mhw','observed','dynamic','statistical'])]

def fit_cells(x,y,future,alpha=10.):
    """x: cells x times x features. Training-only scaling, penalised logit."""
    mean=x.mean(axis=1,keepdims=True);scale=np.maximum(x.std(axis=1,keepdims=True),1e-8)
    x=(x-mean)/scale;future=(future-mean[:,0])/scale[:,0]
    d=np.concatenate([np.ones((*x.shape[:2],1)),x],axis=2)
    e=np.column_stack([np.ones(len(x)),future])
    labels=y.T;prevalence=(labels.sum(axis=1)+.5)/(labels.shape[1]+1)
    b=np.zeros((len(x),d.shape[2]));b[:,0]=np.log(prevalence/(1-prevalence))
    varying=(labels.sum(axis=1)>0)&(labels.sum(axis=1)<labels.shape[1])
    if varying.any():
        dv=d[varying];yv=labels[varying];bv=b[varying].copy()
        penalty=np.r_[1e-6,np.full(x.shape[2],alpha)]
        for _ in range(50):
            pr=expit(np.einsum('ctp,cp->ct',dv,bv));w=np.maximum(pr*(1-pr),1e-8)
            g=np.einsum('ctp,ct->cp',dv,pr-yv)+bv*penalty
            h=np.einsum('ctp,ct,ctq->cpq',dv,w,dv)+np.diag(penalty)[None]
            step=np.linalg.solve(h,g[...,None])[...,0]
            bv-=step/np.maximum(1,np.max(abs(step),axis=1)/3)[:,None]
            if np.max(abs(step))<1e-7:break
        assert np.isfinite(bv).all()
        b[varying]=bv
    return expit(np.einsum('cp,cp->c',e,b))

def local_sst(years,months):
    """Real daily OISST, matched to the same pre-issue months each year."""
    meta=json.loads((D/'metadata.json').read_text());n=len(meta['products']['oisst']['cells'])
    result=np.full((len(years),n),np.nan);offset=0
    for basin in ['redsea','gulf','eastasia']:
        root=ROOT/'dist/detail/daily'/basin;j=json.loads((root/'index.json').read_text())
        dates=pd.DatetimeIndex(j['dates'])
        masks=[(dates.year==y)&np.isin(dates.month,months) for y in years]
        for i,file in enumerate(j['files']):
            a=np.fromfile(root/file['file'],dtype='<i2').astype(float)
            a[a==-32768]=np.nan;a*=.01
            for k,mask in enumerate(masks):
                if mask.any() and np.isfinite(a[mask]).all():result[k,offset+i]=a[mask].mean()
        offset+=len(j['cells'])
    ix=json.loads((ROOT/'dist/observed2026/oisst/index.json').read_text());dates=pd.DatetimeIndex(ix['dates'])
    for k,y in enumerate(years):
        if y!=2026:continue
        mask=np.isin(dates.month,months)
        for start in range(0,n,ix['chunkSize']):
            path=ROOT/f'dist/observed2026/oisst/{start//ix["chunkSize"]:04d}/sst.bin.gz'
            a=np.frombuffer(gzip.decompress(path.read_bytes()),dtype='<i2').reshape(-1,len(dates)).astype(float)
            assert np.all(a[:,mask]!=-32768)
            result[k,start:start+len(a)]=a[:,mask].mean(axis=1)*.01
    assert np.isfinite(result).all()
    return result

def recent_mhw(product,years,months):
    j=json.loads((ROOT/'dist/detail/monthly/index.json').read_text());info=j['products'][product]
    dates=pd.DatetimeIndex(info['dates']);n=len(json.loads((D/'metadata.json').read_text())['products'][product]['cells'])
    result=np.empty((len(years),n))
    ix=json.loads((ROOT/f'dist/observed2026/{product}/index.json').read_text())
    current=np.frombuffer(gzip.decompress((ROOT/f'dist/observed2026/{product}'/ix['monthlyFile']).read_bytes()),dtype='u1').reshape(n,-1)
    for start in range(0,n,j['chunkCells']):
        a=np.fromfile(ROOT/f'dist/detail/monthly/{product}_{start//j["chunkCells"]}.u8',dtype='u1').reshape(-1,len(dates))
        for k,y in enumerate(years):
            if y==2026:
                mask=np.isin(pd.DatetimeIndex(ix['monthDates']).month,months)
                assert mask.sum()==len(months)
                result[k,start:start+len(a)]=current[start:start+len(a),mask].sum(axis=1)
            else:
                mask=(dates.year==y)&np.isin(dates.month,months);assert mask.sum()==len(months)
                result[k,start:start+len(a)]=a[:,mask].sum(axis=1)
    return result

def run(product,limit=None):
    OUT.mkdir(parents=True,exist_ok=True)
    meta=json.loads((D/'metadata.json').read_text());old=json.loads((D/'outlook.json').read_text())
    info=meta['products'][product];prior=old['pixelOutlooks'][product]
    # This release is a matched October-issue DJF comparison, not a generic
    # monthly rollover. Fail closed rather than silently reusing wrong leads.
    assert prior['season']=='DJF' and prior['issueDate'].startswith('2026-10')
    cases=pd.read_csv(D/'seasonal_training.csv');t=cases[(cases['product']==info['name'])&(cases.season=='DJF')&(cases.lead_months==2)]
    first=t.iloc[0];t=t[(t.habitat==first.habitat)&(t.region==first.region)].sort_values('season_start_year')
    years=t.season_start_year.to_numpy(int);n=len(info['cells']);positions=np.searchsorted(info['years'],years)
    y=np.fromfile(D/f'{product}_season_DJF.f32',dtype='<f4').reshape(-1,n)[positions].astype(float)
    extra=certified_2025(product,info);assert extra is not None
    years=np.r_[years,2025];y=np.vstack([y,extra]);all_years=np.r_[years,2026]
    modes=prior['modes'];live=json.loads((D/'climate_latest.json').read_text());dates=pd.DatetimeIndex(live['monthly']['dates'])
    observed=np.array([[np.mean(np.asarray(live['monthly']['values'][m],float)[(dates.year==yr)&np.isin(dates.month,[6,7,8])]) for m in modes] for yr in all_years]);assert np.isfinite(observed).all()
    cache=ROOT/'_cache'/f'outlook_local_sst_{all_years[0]}_2026.npy'
    if cache.exists():sst=np.load(cache)
    else:sst=local_sst(all_years,[6,7,8]);np.save(cache,sst)
    # Nearest real OISST source for local SST; no interpolation or invented MUR SST.
    def xyz(c):
        v=np.deg2rad(c);return np.column_stack([np.cos(v[:,1])*np.cos(v[:,0]),np.cos(v[:,1])*np.sin(v[:,0]),np.sin(v[:,1])])
    distance,source=cKDTree(xyz(meta['products']['oisst']['cells'])).query(xyz(info['cells']))
    mhw=recent_mhw(product,all_years,[6,7,8])
    archive=json.loads((OUT/'iri_families.json').read_text());byyear={int(v['issueMonth'][:4]):v for v in archive}
    forecast={key:np.array([byyear.get(int(yr),{}).get('families',{}).get(key,{}).get('DJF',np.nan) for yr in all_years]) for key in ['combined','dynamic','statistical']}
    test_years=np.arange(2016,2026);test_positions=[int(np.where(years==yr)[0][0]) for yr in test_years]
    # Explicit sample mode for fast independent tests; full native arrays otherwise.
    cells=np.arange(n) if limit is None else np.unique(np.linspace(0,n-1,limit).astype(int))
    nout=len(cells);pred=np.empty((len(SPECS),len(test_years),nout),dtype='<f4');current=np.empty((len(SPECS),nout),dtype='<f4')
    truth=np.empty((len(test_years),nout),dtype='<f4');threshold=None
    start_time=time.time()
    for origin,k in enumerate([*test_positions,len(years)]):
        cut=np.maximum(10,np.quantile(y[:k],.8,axis=0));labels=y[:k]>cut
        base=(labels.sum(axis=0)+.5)/(k+1)
        if k<len(years):truth[origin]=(y[k,cells]>cut[cells])
        else:threshold=cut[cells]
        for c,(key,label,features) in enumerate(SPECS):
            if not features:prob=base[cells]
            else:
                usable=np.ones(k,dtype=bool)
                for f in features:
                    if f in forecast:usable &= np.isfinite(forecast[f][:k])
                assert usable.sum()>=8
                prob=np.empty(nout)
                for a in range(0,nout,1024):
                    ids=cells[a:a+1024];size=len(ids);parts=[]
                    for f in features:
                        if f=='year':v=np.broadcast_to(all_years[:,None,None],(len(all_years),size,1))
                        elif f=='sst':v=sst[:,source[ids],None]
                        elif f=='mhw':v=mhw[:,ids,None]
                        elif f=='observed':v=np.broadcast_to(observed[:,None,:],(len(all_years),size,len(modes)))
                        elif f=='pacific':v=np.broadcast_to(observed[:,None,[modes.index('Nino34'),modes.index('PDO')]],(len(all_years),size,2))
                        else:v=np.broadcast_to(forecast[f][:,None,None],(len(all_years),size,1))
                        parts.append(v)
                    x=np.concatenate(parts,axis=2)
                    prob[a:a+size]=fit_cells(x[:k][usable].transpose(1,0,2),labels[:k,ids][usable],x[k])
            if k<len(years):pred[c,origin]=prob
            else:current[c]=prob
        print(product,'origin',int(all_years[k]),'cells',nout,'seconds',round(time.time()-start_time),flush=True)
    post=test_years >= (2023 if product=='mur' else 2012)
    loss=(pred-truth[None])**2;brier=loss[:,post].mean(axis=1);skill=1-brier/np.maximum(brier[0],1e-12)
    # Evaluate the architecture-selection procedure, never its in-sample winner.
    policy=pred[0].copy();choices=np.zeros((len(test_years),nout),dtype=np.int16)
    for i in range(len(test_years)):
        if i>=4:
            choice=np.argmin(loss[:,:i].mean(axis=1),axis=0)
            choices[i]=choice;policy[i]=pred[choice,i,np.arange(nout)]
    choice=np.argmin(loss.mean(axis=1),axis=0);policy_current=current[choice,np.arange(nout)]
    policy_skill=1-((policy[post]-truth[post])**2).mean(axis=0)/np.maximum(brier[0],1e-12)
    # Paired year bootstrap of policy-minus-published squared errors. This
    # assesses the procedure, not the individually best-looking candidate.
    previous=json.loads((ROOT/'dist/forecasts/cell_models.json').read_text())['products'][product]
    original=np.fromfile(ROOT/'dist/forecasts'/previous['files']['backtest_predictions'],dtype='<f4').reshape(-1,n)
    original=original[[previous['testYears'].index(int(yr)) for yr in test_years]][:,cells]
    gain=(original-truth)**2-(policy-truth)**2
    rng=np.random.default_rng(3617);draws=rng.integers(0,post.sum(),size=(1000,int(post.sum())))
    # Bound memory by cells. Simultaneous spatial evidence is not asserted.
    low=np.empty(nout);high=np.empty(nout)
    for start in range(0,nout,1024):
        boot=gain[post,start:start+1024][draws].mean(axis=1)
        low[start:start+1024],high[start:start+1024]=np.quantile(boot,[.025,.975],axis=0)
    arrays={'candidate_probability':current,'candidate_skill':skill,'candidate_brier':brier,
            'candidate_backtest':pred,'truth':truth,'policy_backtest':policy,'policy_probability':policy_current,
            'policy_skill':policy_skill,'selected_candidate':choice,'threshold':threshold,
            'gain_lower':low,'gain_upper':high,'sst_source':source[cells],'sst_distance_km':2*np.arcsin(distance[cells]/2)*6371}
    folder=OUT/(product if limit is None else product+'_sample');folder.mkdir(exist_ok=True)
    for name,value in arrays.items():np.asarray(value,dtype='<f4').tofile(folder/(name+'.f32'))
    report={'product':product,'nativeCells':nout,'cellIds':cells.tolist() if limit else None,
      'issueMonth':'2026-10','seasonStart':'2026-12-01','seasonEnd':'2027-02-28',
      'testYears':test_years.tolist(),'postBaselineMask':post.tolist(),'nTest':int(post.sum()),
      'candidates':[{'id':v[0],'name':v[1],'features':v[2]} for v in SPECS],
      'penalty':10,'predictorMonths':'June–August of issue year','newDefaultApplied':False,
      'selection':'Earlier test losses only; four earlier origins before architecture selection. Current candidate is the minimum earlier Brier loss.',
      'arrayLayout':'candidate-major, then test-year if present, then native cell; little-endian float32',
      'localSst':'Nearest retained OISST source, with source ID and distance; MHW outcomes and recent MHW counts use the selected native product.',
      'medianPolicySkill':float(np.median(policy_skill)),'positivePolicySkillPercent':float((policy_skill>0).mean()*100),
      'positiveGainLowerBoundCells':int((low>0).sum()),
      'baselineAvailabilityNote':'MUR has three post-baseline seasons. Earlier tests are retrospective, not operational validation.',
      'candidateMedianSkill':{v[0]:float(np.median(skill[i])) for i,v in enumerate(SPECS)},
      'files':{name:f'{folder.name}/{name}.f32' for name in arrays}}
    (folder/'summary.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k in ['product','nativeCells','medianPolicySkill','positivePolicySkillPercent','positiveGainLowerBoundCells','candidateMedianSkill']}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--product',choices=['mur','oisst'],required=True);p.add_argument('--limit',type=int)
    a=p.parse_args();run(a.product,a.limit)
