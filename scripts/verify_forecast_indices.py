"""Independent point fits and structural checks for issued-index forecasts."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit
from external_index_forecasts import iri_svg
from forecast_index_models import certified_2025

ROOT=Path(__file__).resolve().parents[1];D=ROOT/'dist/data';F=ROOT/'dist/forecasts'

def independent_fit(years,x,labels,year,future,alpha):
    # Independent detrending/scaling and penalised Bernoulli optimisation.
    trend=np.column_stack([np.ones(len(years)),years-years.mean()])
    coef=np.linalg.lstsq(trend,x,rcond=None)[0];res=x-trend@coef
    scale=np.maximum(res.std(axis=0),1e-8);mean=res.mean(axis=0)
    design=np.column_stack([np.ones(len(years)),(res-mean)/scale])
    e=np.r_[1,(future-np.r_[1,year-years.mean()]@coef-mean)/scale]
    def objective(beta):
        z=design@beta;pen=np.r_[1e-6,np.full(x.shape[1],alpha)]
        return np.logaddexp(0,z).sum()-labels@z+.5*np.sum(pen*beta**2),design.T@(expit(z)-labels)+pen*beta
    if labels.min()==labels.max():return float((labels.sum()+.5)/(len(labels)+1))
    fit=minimize(objective,np.zeros(design.shape[1]),method='BFGS',jac=True,options={'gtol':1e-9})
    assert np.max(np.abs(objective(fit.x)[1]))<1e-5
    return float(expit(e@fit.x))

def main():
    archive=json.loads((F/'iri_issue_archive.json').read_text());issued={int(x['issueMonth'][:4]):x['seasons']['DJF'] for x in archive}
    for record in archive:
        raw=(ROOT/f"_cache/climate_forecasts/IRI_{record['issueMonth'].replace('-','')}_figure.svg").read_bytes()
        assert iri_svg(raw)==record['seasons']
    model=json.loads((F/'cell_models.json').read_text());meta=json.loads((D/'metadata.json').read_text());old=json.loads((D/'outlook.json').read_text());cases=pd.read_csv(D/'seasonal_training.csv');live=json.loads((D/'climate_latest.json').read_text())
    checked=0;maximum=0
    for product,info in model['products'].items():
        n=info['nativeCells'];load=lambda name:np.fromfile(F/info['files'][name],dtype='<f4')
        p,ref,candidate,w=[load(name) for name in ['probability','reference_probability','candidate_probability','selected_weight']]
        assert np.isfinite(p).all() and np.all((p>=0)&(p<=1));assert np.max(np.abs(p-(ref+w*(candidate-ref))))<1e-6
        if info['nTest']<8:assert np.all(w==0)
        nt=len(info['testYears']);truth=load('backtest_observed').reshape(nt,n);bp=load('reference_predictions').reshape(nt,n);cp=load('candidate_predictions').reshape(nt,n)
        weights=np.array([0,.5,1.]);loss=(bp[None,:,:]+weights[:,None,None]*(cp-bp)[None,:,:]-truth[None,:,:])**2
        nested=bp.copy()
        for i in range(4,nt):
            choice=np.argmin(loss[:,:i].mean(axis=1),axis=0);nested[i]=bp[i]+weights[choice]*(cp[i]-bp[i])
        post=np.array(info['postBaselineMask']);policy=bp.copy()
        for i in range(nt):
            before=post & (np.arange(nt)<i)
            if before.sum()>=8:
                gain=np.mean((bp[before]-truth[before])**2-(nested[before]-truth[before])**2,axis=0)
                policy[i]=np.where(gain>0,nested[i],bp[i])
        assert np.max(np.abs(policy-load('backtest_predictions').reshape(nt,n)))<1e-6
        assert np.max(np.abs(np.mean((policy[post]-truth[post])**2,axis=0)-load('brier')))<1e-6
        modes=old['pixelOutlooks'][product]['modes'];t=cases[(cases['product']==meta['products'][product]['name'])&(cases.season=='DJF')&(cases.lead_months==2)];first=t.iloc[0];t=t[(t.habitat==first.habitat)&(t.region==first.region)].sort_values('season_start_year');years=t.season_start_year.to_numpy();x=t[modes].to_numpy();positions=np.searchsorted(meta['products'][product]['years'],years);y=np.fromfile(D/f'{product}_season_DJF.f32',dtype='<f4').reshape(-1,n)[positions]
        def indices(year):
            k=[i for i,date in enumerate(live['monthly']['dates']) if date[:4]==str(year) and date[5:7] in ['06','07','08']]
            return np.array([np.mean([live['monthly']['values'][m][i] for i in k]) for m in modes])
        extra=certified_2025(product,meta['products'][product])
        if extra is not None:years=np.r_[years,2025];x=np.vstack([x,indices(2025)]);y=np.vstack([y,extra])
        cut=np.maximum(10,np.quantile(y,.8,axis=0));common=np.array([v in issued for v in years]);cx=np.column_stack([x[common],[issued[v] for v in years[common]]]);cy=years[common];future=np.r_[indices(2026),issued[2026]]
        for cell in np.unique(np.r_[np.linspace(0,n-1,7).astype(int),np.argmax(w),np.argmin(candidate),np.argmax(candidate)]):
            loss=[]
            for k,year in enumerate(years):
                if year not in issued or (cy<year).sum()<8:continue
                keep=cy<year;threshold=max(10,np.quantile(y[:k,cell],.8));labels=(y[common,cell][:keep.sum()]>threshold).astype(float)
                predictions=[independent_fit(cy[keep],cx[keep],labels,year,np.r_[indices(year),issued[year]],a) for a in [1,10,100]]
                truth=y[k,cell]>threshold;loss.append((np.array(predictions)-truth)**2)
            alpha=[1,10,100][np.argmin(np.mean(loss,axis=0))]
            result=independent_fit(cy,cx,(y[common,cell]>cut[cell]).astype(float),2026,future,alpha)
            difference=abs(result-float(candidate[cell]));maximum=max(maximum,difference);assert difference<2e-5,(product,int(cell),difference);checked+=1
    (ROOT/'qa/issued_forecast_validation.json').write_text(json.dumps({'passed':True,'archivedOctoberIssues':len(archive),'independentPointFits':checked,'maximumDifference':maximum,'noRealisedFutureIndexInputs':True},indent=2))
    print(f'PASS: {len(archive)} published October issues, {checked} independent point fits; maximum difference {maximum:.2g}.')

if __name__=='__main__':main()
