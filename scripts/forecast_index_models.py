"""Chronological cell models using IRI's already-issued DJF ENSO forecasts.

Six observed lagged indices remain the reference. The extra predictor is the
published October IRI combined-average DJF forecast, not realised winter ENSO.
Thresholds use the full earlier outcome record for both models. Only complete
DJF seasons enter training; December 2025–February 2026 is added when certified.
Model/penalty/blend choices use earlier origins only. A minimum eight seasons
after fixed-baseline availability is required before replacing the reference.
"""
from pathlib import Path
from datetime import datetime,timezone
import gzip,json
import numpy as np
import pandas as pd
from scipy.special import expit
from pixel_outlook import design,solve_unique,ALPHAS

ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'dist/data';OUT=ROOT/'dist/forecasts'

def certified_2025(product,info):
    mf=json.loads((ROOT/'dist/observed2026/manifest.json').read_text())
    if product not in mf['products']:return None
    ix=json.loads((ROOT/'dist/observed2026'/mf['products'][product]['index']).read_text())
    if not ix.get('previousDecemberTailAdditionalDaysFile'):return None
    months=np.frombuffer(gzip.decompress((ROOT/'dist/observed2026'/product/ix['monthlyFile']).read_bytes()),dtype='u1').reshape(len(info['cells']),len(ix['monthDates']))
    assert ix['monthDates'][:2]==['2026-01','2026-02'] or [x[:7] for x in ix['monthDates'][:2]]==['2026-01','2026-02']
    # Complete December 2025 from the original verified monthly display arrays.
    monthly=json.loads((ROOT/'dist/detail/monthly/index.json').read_text());p=monthly['products'][product]
    december=p['dates'].index('2025-12-15');width=monthly['chunkCells'];dec=np.empty(len(info['cells']))
    for start in range(0,len(dec),width):
        a=np.fromfile(ROOT/f'dist/detail/monthly/{product}_{start//width}.u8',dtype='u1').reshape(-1,len(p['dates']))
        dec[start:start+len(a)]=a[:,december]
    tail=np.frombuffer(gzip.decompress((ROOT/'dist/observed2026'/product/ix['previousDecemberTailAdditionalDaysFile']).read_bytes()),dtype='u1');assert len(tail)==len(dec) and tail.max()<=6
    assert np.all(dec+tail<=31),'Confirmed December membership exceeds the calendar month; review the boundary inputs.'
    return dec+tail+months[:,:2].sum(axis=1)

def refit(years,x,y,fyear,fx,alphas):
    cut=np.maximum(10,np.quantile(y,.8,axis=0));labels=(y.T>cut[:,None]).astype('u1')
    unique,inverse=np.unique(labels,axis=0,return_inverse=True);d,e=design(years,x,fyear,fx)
    result=np.empty(y.shape[1])
    for a in np.unique(alphas):
        use=alphas==a;result[use]=expit(solve_unique(d,unique,float(a))@e)[inverse[use]]
    return result,cut

def main():
    OUT.mkdir(exist_ok=True);meta=json.loads((DATA/'metadata.json').read_text());old=json.loads((DATA/'outlook.json').read_text())
    archive=json.loads((OUT/'iri_issue_archive.json').read_text());current=next(iter(old['pixelOutlooks'].values()));season=current['season'];future_year=int(current['seasonStart'][:4]);external={int(p['issueMonth'][:4])+future_year-int(current['issueDate'][:4]):p['seasons'][season] for p in archive if season in p['seasons']};template=next(t for t in old['targets'] if t.get('available'));window=pd.period_range(template['predictorFirstMonth'],template['predictorLastMonth'],freq='M')
    assert archive[-1]['issueMonth']==current['issueDate'][:7], 'The matching issued index forecast is not yet available'
    live=json.loads((DATA/'climate_latest.json').read_text());cases=pd.read_csv(DATA/'seasonal_training.csv')
    report={'asOf':datetime.now(timezone.utc).isoformat(),'referenceAsOf':old['asOf'],'season':season,'seasonStart':current['seasonStart'],'seasonEnd':current['seasonEnd'],
        'forecastIssueMonth':archive[-1]['issueMonth'],'externalProvider':'Columbia/IRI','externalSource':archive[-1]['source'],
        'extraPredictor':f'Published {archive[-1]["issueMonth"][5:7]}-issue {season} Niño-3.4 forecast (degC)','externalForecastValue':external[future_year],
        'selection':'Chronological regularisation and blend selection using earlier origins only; retain reference unless at least 8 post-baseline test seasons and positive nested Brier gain.',
        'binaryDtype':'little-endian float32','binaryLayout':'one value per native source cell; backtest arrays are test-year-major, then native cell','iodUsedInCellModel':False,'iodReason':'Current JAMSTEC IOD forecast is displayed; a matching archived-issue hindcast is not yet available.',
        'references':['https://www.nature.com/articles/s41586-022-04573-9','https://os.copernicus.org/articles/20/265/2024/'],'products':{}}
    for product,info in meta['products'].items():
        previous=old['pixelOutlooks'][product]
        modes=previous['modes'];canonical=cases[(cases['product']==info['name'])&(cases.season==season)&(cases.lead_months==previous['leadMonths'])]
        first=canonical.iloc[0];train=canonical[(canonical.habitat==first.habitat)&(canonical.region==first.region)].sort_values('season_start_year')
        years=train.season_start_year.to_numpy(int);n=len(info['cells']);positions=np.searchsorted(info['years'],years)
        y=np.fromfile(DATA/f'{product}_season_{season}.f32',dtype='<f4').reshape(len(info['years']),n)[positions].astype(float)
        x=train[modes].to_numpy(float)
        def index_values(year):
            wanted={str(p-(future_year-year)*12) for p in window};indices=[i for i,date in enumerate(live['monthly']['dates']) if date[:7] in wanted]
            assert len(indices)==3
            return np.array([np.mean([live['monthly']['values'][m][i] for i in indices]) for m in modes])
        added=certified_2025(product,info) if season=='DJF' and years[-1]==2024 else None
        if added is not None:years=np.r_[years,2025];y=np.vstack([y,added]);x=np.vstack([x,index_values(2025)])
        assert np.isfinite(y).all() and np.isfinite(x).all()
        alphas=np.fromfile(DATA/f'{product}_outlook_alpha.f32',dtype='<f4')
        base_years=np.array(previous['testYears']);base=np.fromfile(DATA/f'{product}_outlook_backtest_predictions.f32',dtype='<f4').reshape(len(base_years),n)
        if added is not None:
            pred,_=refit(years[:-1],x[:-1],y[:-1],2025,x[-1],alphas);base=np.vstack([base,pred]);base_years=np.r_[base_years,2025]
        base_current,threshold=refit(years,x,y,future_year,index_values(future_year),alphas)
        penalties=[1.,10.,100.];candidate_probs=[];candidate_truth=[];candidate_bases=[];climatologies=[];test_years=[];inner_loss=[]
        common=np.array([v in external for v in years]);cx=np.column_stack([x[common],[external[v] for v in years[common]]]);cy=years[common]
        origin_indices=[k for k,v in enumerate(years) if v in external and (cy<v).sum()>=8]
        for k in [*origin_indices,len(years)]:
            future=k==len(years);year=future_year if future else years[k];keep=cy<year
            d,e=design(cy[keep],cx[keep],year,np.r_[index_values(year),external[year]])
            cut=np.maximum(10,np.quantile(y[:k],.8,axis=0));labels=(y[common][:keep.sum()].T>cut[:,None]).astype('u1')
            unique,inverse=np.unique(labels,axis=0,return_inverse=True)
            probs=np.array([expit(solve_unique(d,unique,a)@e)[inverse] for a in penalties])
            if inner_loss:
                selected=np.argmin(np.mean(inner_loss,axis=0),axis=0)
            else:selected=np.full(n,2)
            selected_p=probs[selected,np.arange(n)]
            if future:candidate_current=selected_p;break
            truth=(y[k]>cut).astype(float);inner_loss.append((probs-truth)**2)
            candidate_probs.append(selected_p);candidate_truth.append(truth);test_years.append(int(year))
            climatologies.append(((y[:k]>cut).sum(axis=0)+.5)/(k+1))
            j=np.where(base_years==year)[0]
            candidate_bases.append(base[j[0]] if len(j) else np.full(n,np.nan))
            print(product,'external forecast origin',year,'unique histories',len(unique),flush=True)
        cp=np.array(candidate_probs);truth=np.array(candidate_truth);bp=np.array(candidate_bases);climatologies=np.array(climatologies);test_years=np.array(test_years)
        valid=np.isfinite(bp).all(axis=1);cp,truth,bp,climatologies,test_years=cp[valid],truth[valid],bp[valid],climatologies[valid],test_years[valid]
        # Four earlier scored origins precede any architecture/blend choice.
        weights=np.array([0,.5,1.]);nested=[];loss=(bp[None,:,:]+weights[:,None,None]*(cp-bp)[None,:,:]-truth[None,:,:])**2
        for i in range(len(test_years)):
            choice=np.argmin(loss[:,:i].mean(axis=1),axis=0) if i>=4 else np.zeros(n,dtype=int)
            nested.append(bp[i]+weights[choice]*(cp[i]-bp[i]))
        nested=np.array(nested);post=(test_years>= (2023 if product=='mur' else 2012)) & (np.arange(len(test_years))>=4)
        candidate_brier=np.mean((nested[post]-truth[post])**2,axis=0);base_brier=np.mean((bp[post]-truth[post])**2,axis=0)
        selected=np.argmin(loss.mean(axis=1),axis=0);w=weights[selected]
        promote=(post.sum()>=8)&(candidate_brier<base_brier)&(w>0)
        used=np.where(promote,w,0);prob=base_current+used*(candidate_current-base_current)
        # Reproduce the same promotion gate at each earlier origin. Eight test
        # seasons must already exist, and every comparison excludes that origin.
        policy=bp.copy()
        for i in range(len(test_years)):
            before=post & (np.arange(len(test_years))<i)
            if before.sum()>=8:
                gain=np.mean((bp[before]-truth[before])**2-(nested[before]-truth[before])**2,axis=0)
                policy[i]=np.where(gain>0,nested[i],bp[i])
        brier=np.mean((policy[post]-truth[post])**2,axis=0)
        climatology_brier=np.mean((climatologies[post]-truth[post])**2,axis=0)
        skill=1-brier/np.maximum(climatology_brier,1e-12)
        arrays={'probability':prob,'reference_probability':base_current,'candidate_probability':candidate_current,
            'selected_weight':used,'brier':brier,'reference_brier':base_brier,'gain':base_brier-brier,
            'candidate_gain':base_brier-candidate_brier,'predictions':policy,'reference_predictions':bp,'candidate_predictions':cp,
            'backtest_predictions':policy,'backtest_observed':truth,'backtest_baselines':climatologies,
            'baseline':((y>threshold).sum(axis=0)+.5)/(len(y)+1),'baseline_brier':climatology_brier,
            'skill':skill,'skill_all':1-np.mean((policy-truth)**2,axis=0)/np.maximum(np.mean((climatologies-truth)**2,axis=0),1e-12),
            'n_high':truth[post].sum(axis=0),'alpha':alphas,'observed':truth,'threshold':threshold,'latest_season_days':y[-1]}
        for name,a in arrays.items():np.asarray(a,dtype='<f4').tofile(OUT/f'{product}_{name}.f32')
        report['products'][product]={'nativeCells':n,'issueDate':report['asOf'][:10],'trainingYears':years.tolist(),'testYears':test_years.tolist(),
            'postBaselineMask':post.tolist(),'nTest':int(post.sum()),'promotedCells':int(promote.sum()),
            'nTestRetrospective':len(test_years),
            'completedDJF2025Added':added is not None,'medianBrierGain':float(np.median(base_brier-brier)),
            'probabilityFile':f'{product}_probability.f32','files':{name:f'{product}_{name}.f32' for name in arrays},
            'method':'Six observed lagged indices plus an archived issued ENSO forecast; ridge logistic model, training-only detrending and scaling.',
            'referenceMethod':'Original six-index model; its pre-2025 regularisation is frozen when adding the new complete 2025 DJF season.'}
        (OUT/'cell_models.json').write_text(json.dumps(report,indent=2),encoding='utf8')
        print(product,'external forecast test seasons',int(post.sum()),'promoted cells',int(promote.sum()),flush=True)

if __name__=='__main__':main()
