"""Refresh NOAA monthly feeds and produce next-season habitat-model estimates.

Study-period climate values and the pixel arrays remain unchanged. Network errors
leave the last successfully generated outlook in place and fail the scheduled job.
"""
from __future__ import annotations
import argparse
import calendar
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd
from scipy.special import expit
from pixel_outlook import predict_all

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'dist/data'
MODES = ['Nino34','IOD','NAO','AO','EAWR','NAtl_SSTA','PDO']
SOURCES = {
    'Nino34':'https://www.cpc.ncep.noaa.gov/data/indices/sstoi.indices',
    'IOD':'https://psl.noaa.gov/gcos_wgsp/Timeseries/Data/dmi.had.long.data',
    'NAO':'https://ftp.cpc.ncep.noaa.gov/wd52dg/data/indices/nao_index.tim',
    'AO':'https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.index.b500101.current.ascii',
    'EAWR':'https://ftp.cpc.ncep.noaa.gov/wd52dg/data/indices/eawr_index.tim',
    'NAtl_SSTA':'https://www.ncei.noaa.gov/pub/data/cmb/ersst/v5/index/ersst.v5.amo.dat',
    'PDO':'https://www.ncei.noaa.gov/pub/data/cmb/ersst/v5/index/ersst.v5.pdo.dat',
}


def parse(text, mode):
    rows=[]
    ao_dates={}
    for line in text.splitlines():
        p=line.split()
        if not p or not p[0].isdigit():
            continue
        year=int(p[0])
        if not 1900 <= year <= 2100:
            continue
        if mode=='Nino34' and len(p)>=10 and p[1].isdigit():
            rows.append([year,int(p[1]),float(p[9])])
        elif mode in ['IOD','PDO'] and len(p)==13:
            rows.extend([year,m,float(v)] for m,v in enumerate(p[1:],1))
        elif mode in ['NAO','EAWR','NAtl_SSTA'] and len(p)==3 and p[1].isdigit():
            rows.append([year,int(p[1]),float(p[2])])
        elif mode=='AO' and len(p)==4 and p[1].isdigit():
            rows.append([year,int(p[1]),float(p[3])])
            ao_dates.setdefault((year,int(p[1])),set()).add(int(p[2]))
    frame=pd.DataFrame(rows,columns=['year','month',mode])
    if frame.empty:
        raise ValueError(f'Unable to parse NOAA {mode} archive')
    frame=frame[(frame.month>=1)&(frame.month<=12)&(frame[mode].abs()<90)]
    monthly=frame.groupby(['year','month'],as_index=False)[mode].mean()
    if mode=='AO':
        complete=monthly.apply(lambda r:len(ao_dates[(int(r.year),int(r.month))])==calendar.monthrange(int(r.year),int(r.month))[1],axis=1)
        monthly=monthly[complete]
    return monthly


def ridge_logistic(design,label,alpha):
    prevalence=(label.sum()+.5)/(len(label)+1)
    beta=np.zeros(design.shape[1]);beta[0]=np.log(prevalence/(1-prevalence))
    if len(np.unique(label))<2:
        return beta
    penalty=np.diag([1e-6]+[alpha]*(design.shape[1]-1))
    for _ in range(35):
        probability=expit(design@beta)
        gradient=design.T@(probability-label)+penalty@beta
        hessian=(design.T*np.maximum(probability*(1-probability),1e-8))@design+penalty
        step=np.linalg.solve(hessian,gradient)
        beta-=step/max(1.,float(np.max(np.abs(step)))/3.)
        if np.max(np.abs(step))<1e-7:
            break
    return beta


def cutoff(train):
    return max(10.,float(np.quantile(train.observed_mhw_days,.8)))


def fit_probability(train, year, indices, alpha, modes=MODES):
    # Identical indices-only transforms to the manuscript seasonal warning code.
    t=train.season_start_year.to_numpy(float)
    bt=np.column_stack([np.ones(len(t)),t-t.mean()])
    be=np.array([[1.,year-t.mean()]])
    x=train[modes].to_numpy(float)
    trend=np.linalg.lstsq(bt,x,rcond=None)[0]
    a=x-bt@trend
    ae=np.asarray(indices,float)[None,:]-be@trend
    mu=a.mean(axis=0);scale=np.maximum(a.std(axis=0),1e-8)
    d=np.column_stack([np.ones(len(a)),(a-mu)/scale])
    e=np.column_stack([np.ones(len(ae)),(ae-mu)/scale])
    label=(train.observed_mhw_days.to_numpy()>cutoff(train)).astype(float)
    beta=ridge_logistic(d,label,alpha)
    return float(expit(e@beta)[0]),dict(beta=beta.tolist(),mean=mu.tolist(),scale=scale.tolist(),climateTrend=trend.tolist(),yearMean=float(t.mean()))


def best_alpha(train,modes=MODES,cache=None):
    cache={} if cache is None else cache
    errors=[]
    for alpha in [.1,1.,10.,100.]:
        losses=[]
        for k in range(max(8,len(train)//2),len(train)):
            previous=train.iloc[:k];test=train.iloc[k]
            key=(alpha,k)
            if key not in cache:
                probability=fit_probability(previous,int(test.season_start_year),test[modes].to_numpy(float),alpha,modes)[0]
                cache[key]=(probability-int(test.observed_mhw_days>cutoff(previous)))**2
            losses.append(cache[key])
        errors.append(np.mean(losses))
    return [.1,1.,10.,100.][int(np.argmin(errors))]


def backtest(train,modes,product,cache):
    rows=[]
    for k in range(12,len(train)):
        past=train.iloc[:k];test=train.iloc[k]
        alpha=best_alpha(past,modes,cache)
        probability=fit_probability(past,int(test.season_start_year),test[modes].to_numpy(float),alpha,modes)[0]
        label=(past.observed_mhw_days.to_numpy()>cutoff(past)).astype(float)
        baseline=float((label.sum()+.5)/(len(label)+1))
        rows.append({'year':int(test.season_start_year),'probability':probability,'baseline':baseline,
            'observedHigh':int(test.observed_mhw_days>cutoff(past)),
            'baselineAvailable':pd.Timestamp(test.issue_date)>=pd.Timestamp('2023-02-01' if product=='GHRSST MUR' else '2012-02-01')})
    summaries={}
    for scope in ['all_retrospective','baseline_available']:
        subset=[r for r in rows if scope=='all_retrospective' or r['baselineAvailable']]
        if not subset:
            summaries[scope]={'nTest':0,'skill':None};continue
        y=np.array([r['observedHigh'] for r in subset]);p=np.array([r['probability'] for r in subset]);b=np.array([r['baseline'] for r in subset])
        bs=np.mean((y-p)**2);bb=np.mean((y-b)**2)
        summaries[scope]={'nTest':len(y),'nHigh':int(y.sum()),'brierScore':float(bs),'baselineBrierScore':float(bb),
            'skill':float(1-bs/bb) if bb>1e-12 else None,'meanProbability':float(p.mean()),'observedFraction':float(y.mean())}
    return {'scores':summaries,'predictions':rows}


def clean(value):
    if isinstance(value,dict):return {k:clean(v) for k,v in value.items()}
    if isinstance(value,list):return [clean(v) for v in value]
    if isinstance(value,(np.integer,)):return int(value)
    if isinstance(value,(float,np.floating)):return float(value) if np.isfinite(value) else None
    if isinstance(value,(np.bool_,)):return bool(value)
    return value


def write_json(name,value):
    path=DATA/name
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(clean(value),separators=(',',':'),allow_nan=False),encoding='utf-8')
    temporary.replace(path)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--as-of',help='UTC date for reproducible checks; otherwise today')
    args=parser.parse_args()
    now=pd.Timestamp(args.as_of) if args.as_of else pd.Timestamp.now(tz='UTC').tz_localize(None)
    now=now.normalize()
    def fetch(item):
        mode,url=item
        request=Request(url,headers={'User-Agent':'RedSeaHabitatAtlas/1.0 (academic climate-data update)'})
        with urlopen(request,timeout=60) as response:
            raw=response.read()
        frame=parse(raw.decode('utf-8-sig'),mode)
        print(mode,'latest parsed',f'{int(frame.year.max())}',flush=True)
        return mode,frame,{'url':url,'sha256':hashlib.sha256(raw).hexdigest()}
    results=list(ThreadPoolExecutor(max_workers=4).map(fetch,SOURCES.items()))
    frames={mode:frame for mode,frame,_ in results}
    merged=None
    for mode in MODES:
        f=frames[mode]
        merged=f if merged is None else merged.merge(f,on=['year','month'],how='outer',validate='one_to_one')
    merged=merged.sort_values(['year','month'])
    merged['period']=pd.PeriodIndex(year=merged.year,month=merged.month,freq='M')
    last_complete=now.to_period('M')-1
    merged=merged[(merged.period<=last_complete)&(merged.year>=1982)]
    # AO daily data may end partway through a past month. Require every calendar day.
    # Daily AO grouping includes only completed calendar months; the source's last
    # month is conservatively omitted if it coincides with the current month.
    latest={m:str(merged.loc[merged[m].notna(),'period'].max()) for m in MODES}
    common=merged[MODES].notna().all(axis=1)
    common_last=merged.loc[common,'period'].max()
    if pd.isna(common_last):raise ValueError('No complete seven-index monthly window')
    frozen=json.loads((DATA/'climate.json').read_text(encoding='utf-8'))
    # Preserve the manuscript series through 2025; only append newer feed values.
    frozen_rows=pd.DataFrame({'period':pd.PeriodIndex(pd.to_datetime(frozen['monthly']['dates']),freq='M'),
        **frozen['monthly']['values']})
    fresh=merged[merged.year>=2026][['period',*MODES]]
    combined=pd.concat([frozen_rows,fresh],ignore_index=True).sort_values('period')
    live={'asOf':str(now.date()),'checkedUtc':datetime.now(timezone.utc).isoformat(),
          'commonLastMonth':str(common_last),'latestByMode':latest,'modes':MODES,
          'monthly':{'dates':[str(p)+'-15' for p in combined.period],
                     'values':{m:combined[m].tolist() for m in MODES}},
          'sources':{m:source for m,_,source in results}}
    training=pd.read_csv(DATA/'seasonal_training.csv')
    seasonal_groups=json.loads((DATA/'seasonal_groups.json').read_text())
    metadata=json.loads((DATA/'metadata.json').read_text())
    pixel_metadata={}
    issue=now.replace(day=1)
    targets=[]
    for lead in [1,2,3]:
        target=issue+pd.DateOffset(months=lead)
        if target.month not in [3,6,9,12]:continue
        season={3:'MAM',6:'JJA',9:'SON',12:'DJF'}[target.month]
        predictor_end=issue.to_period('M')-2
        window=pd.period_range(predictor_end-2,predictor_end,freq='M')
        indexed=merged.set_index('period')
        # A fixed six-index panel supplies the live outlook because the HadISST
        # IOD archive is delayed. Its own matched backtest is computed below.
        active_modes=[m for m in MODES if m!='IOD']
        if not window.isin(indexed.index).all() or indexed.loc[window,active_modes].isna().any().any():
            targets.append({'available':False,'season':season,'seasonStart':str(target.date()),
                'reason':f'Waiting for the six outlook indices through {predictor_end}'})
            continue
        indices=indexed.loc[window,active_modes].mean().to_numpy()
        for (product,habitat,region),group in training[(training.season==season)&(training.lead_months==lead)].groupby(['product','habitat','region']):
            train=group[pd.to_datetime(group.season_end)<issue].sort_values('season_start_year')
            assert len(train)>=12
            cache={}
            validation=backtest(train,active_modes,product,cache)
            alpha=best_alpha(train,active_modes,cache)
            probability,model=fit_probability(train,target.year,indices,alpha,active_modes)
            cut=cutoff(train)
            baseline=float(((train.observed_mhw_days>cut).sum()+.5)/(len(train)+1))
            targets.append({'available':True,'product':product,'habitat':habitat,'region':region,
                'scope':'ecoregion','basin':next((b['id'] for b in metadata.get('basins',[]) if metadata['regions'].index(region) in b['regions']),'redsea'),'season':season,'seasonStart':str(target.date()),'seasonEnd':str((target+pd.DateOffset(months=3)-pd.Timedelta(days=1)).date()),
                'leadMonths':lead,'issueDate':str(issue.date()),'predictorFirstMonth':str(window[0]),'predictorLastMonth':str(window[-1]),
                'probability':probability,'historicalProbability':baseline,'highExposureThresholdDays':cut,
                'trainingSeasons':len(train),'trainingFirstYear':int(train.season_start_year.min()),'trainingLastYear':int(train.season_start_year.max()),
                'alpha':alpha,'predictorValues':dict(zip(active_modes,indices.tolist())),
                'modes':active_modes,'backtest':validation,'model':model,'validatedAlert':False})
        for key,product_info in metadata['products'].items():
            product=product_info['name']
            canonical=training[(training['product']==product)&(training.season==season)&(training.lead_months==lead)]
            first=canonical.iloc[0]
            train=canonical[(canonical.habitat==first.habitat)&(canonical.region==first.region)&(pd.to_datetime(canonical.season_end)<issue)].sort_values('season_start_year').copy()
            native_count=len(product_info['cells'])
            years=np.array(product_info['years'])
            year_positions=np.searchsorted(years,train.season_start_year.to_numpy())
            values=np.fromfile(DATA/f'{key}_season_{season}.f32',dtype='<f4').reshape(len(years),native_count)
            outcomes=values[year_positions]
            assert np.isfinite(outcomes).all()
            fitted=predict_all(train.season_start_year.to_numpy(float),train[active_modes].to_numpy(float),outcomes,target.year,indices,product)
            origin_dates=pd.to_datetime(train.issue_date.iloc[12:])
            after_baseline=(origin_dates>=pd.Timestamp('2023-02-01' if key=='mur' else '2012-02-01')).to_numpy()
            def score(select):
                y=fitted['observations'][select];p=fitted['predictions'][select];b=fitted['baselines'][select]
                model_bs=np.mean((y-p)**2,axis=0);reference_bs=np.mean((y-b)**2,axis=0)
                return model_bs,reference_bs,1-model_bs/np.maximum(reference_bs,1e-12),y.sum(axis=0)
            bs,reference_bs,skill,n_high=score(after_baseline)
            _,_,all_skill,_=score(np.ones(len(after_baseline),dtype=bool))
            files={'probability':fitted['probability'],'baseline':fitted['baseline'],'threshold':fitted['threshold'],
                   'alpha':fitted['alpha'],'skill':skill,'skill_all':all_skill,'brier':bs,'baseline_brier':reference_bs,
                   'n_high':n_high,'coefficients':fitted['coefficients'],'backtest_predictions':fitted['predictions'],
                   'backtest_observed':fitted['observations'],'backtest_baselines':fitted['baselines']}
            for name,array in files.items():np.asarray(array,dtype='<f4').tofile(DATA/f'{key}_outlook_{name}.f32')
            pixel_metadata[key]={'season':season,'seasonStart':str(target.date()),'seasonEnd':str((target+pd.DateOffset(months=3)-pd.Timedelta(days=1)).date()),
                'leadMonths':lead,'issueDate':str(issue.date()),'modes':active_modes,'nativeCells':native_count,
                'trainingYears':train.season_start_year.astype(int).tolist(),'testYears':fitted['testYears'].astype(int).tolist(),
                'postBaselineMask':after_baseline.tolist(),'nTest':int(after_baseline.sum()),'nTestRetrospective':len(after_baseline),
                'positiveSkillCells':int((skill>0).sum()),'medianSkill':float(np.median(skill)),
                'model':'Individual source-cell outcomes, thresholds, ridge coefficients and nested chronological regularisation',
                'backtestScope':'post_baseline_availability','validatedAlert':False}
            # Independent pooled outcomes for each whole habitat, not an average
            # of either regional or pixel prediction probabilities.
            pooled=seasonal_groups['products'][key]
            for group_index,group in enumerate(seasonal_groups['groups']):
                if group['scope']!='overall':continue
                overall=train.copy()
                overall['observed_mhw_days']=np.array(pooled['seasons'][season],dtype=float)[year_positions,group_index]
                cache={};validation=backtest(overall,active_modes,product,cache)
                alpha=best_alpha(overall,active_modes,cache)
                probability,model=fit_probability(overall,target.year,indices,alpha,active_modes)
                cut=cutoff(overall)
                template=next(t for t in targets if t.get('product')==product and t.get('available'))
                targets.append({**template,**group,'probability':probability,'highExposureThresholdDays':cut,
                    'historicalProbability':float(((overall.observed_mhw_days>cut).sum()+.5)/(len(overall)+1)),
                    'alpha':alpha,'backtest':validation,'model':model})
    outlook={'asOf':str(now.date()),'updatedUtc':datetime.now(timezone.utc).isoformat(),
             'mhwHistoryThrough':'2025-12','model':'Fixed six-index ridge logistic regression; same transformations and training rules as the manuscript indices-only model, with its own backtest',
             'highExposureDefinition':'Seasonal habitat-cell mean MHW days above the training same-season 80th percentile, with a 10-day floor',
             'targets':targets,'pixelOutlooks':pixel_metadata,'sources':live['sources'],'commonLastMonth':str(common_last)}
    # Write only after all downloads, parsing and forecasts complete successfully.
    write_json('climate_latest.json',live)
    write_json('outlook.json',outlook)
    manifest=json.loads((DATA/'manifest.json').read_text(encoding='utf-8'))
    manifest['files']={str(p.relative_to(ROOT/'dist')).replace('\\','/'):{'bytes':p.stat().st_size,
        'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in DATA.iterdir() if p.is_file() and p.name!='manifest.json'}
    write_json('manifest.json',manifest)
    print('UPDATE READY:',common_last,';',sum(t.get('available',False) for t in targets),'habitat/region outlooks',flush=True)


if __name__=='__main__':main()
