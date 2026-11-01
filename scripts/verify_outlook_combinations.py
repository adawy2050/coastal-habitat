"""Independent optimiser and native-array checks for the new comparisons."""
from pathlib import Path
import json
import numpy as np
from scipy.optimize import minimize
from scipy.special import expit
from test_outlook_combinations import fit_cells

ROOT=Path(__file__).resolve().parents[1]

def scalar(x,y,z):
    mean=x.mean(0);scale=np.maximum(x.std(0),1e-8)
    d=np.column_stack([np.ones(len(x)),(x-mean)/scale]);e=np.r_[1,(z-mean)/scale]
    penalty=np.r_[1e-6,np.full(x.shape[1],10.)]
    def objective(b):
        eta=d@b
        return (np.logaddexp(0,eta).sum()-y@eta+.5*np.sum(penalty*b*b),d.T@(expit(eta)-y)+penalty*b)
    fit=minimize(objective,np.zeros(d.shape[1]),jac=True,method='BFGS',options={'gtol':1e-9})
    assert np.max(abs(objective(fit.x)[1]))<1e-5
    return expit(e@fit.x)

def main():
    rng=np.random.default_rng(817);x=rng.normal(size=(18,22,8));z=rng.normal(size=(18,8));y=rng.binomial(1,.25,size=(22,18))
    p=fit_cells(x,y,z);ref=np.array([scalar(x[i],y[:,i],z[i]) for i in range(18)])
    assert max(abs(p-ref))<1e-6
    results={}
    for product in ['oisst','mur']:
        folder=ROOT/'dist/forecasts/combinations'/product
        if not (folder/'summary.json').exists():continue
        j=json.loads((folder/'summary.json').read_text());n=j['nativeCells'];nt=len(j['testYears']);nc=len(j['candidates'])
        read=lambda name:np.fromfile((folder if (folder/f'{name}.f32').exists() else ROOT/'_cache/outlook_combinations'/product)/f'{name}.f32',dtype='<f4')
        pred=read('candidate_backtest').reshape(nc,nt,n);truth=read('truth').reshape(nt,n);current=read('candidate_probability').reshape(nc,n)
        assert np.isfinite(pred).all() and np.all((pred>=0)&(pred<=1))
        assert np.isfinite(current).all() and np.all((current>=0)&(current<=1))
        old=json.loads((ROOT/'dist/forecasts/cell_models.json').read_text())['products'][product]
        positions=[old['testYears'].index(yr) for yr in j['testYears']]
        old_truth=np.fromfile(ROOT/'dist/forecasts'/old['files']['backtest_observed'],dtype='<f4').reshape(-1,n)[positions]
        old_baseline=np.fromfile(ROOT/'dist/forecasts'/old['files']['backtest_baselines'],dtype='<f4').reshape(-1,n)[positions]
        np.testing.assert_array_equal(truth,old_truth)
        np.testing.assert_allclose(pred[0],old_baseline,atol=1e-7)
        loss=(pred-truth)**2;post=np.array(j['postBaselineMask'])
        brier=loss[:,post].mean(1);np.testing.assert_allclose(brier,read('candidate_brier').reshape(nc,n),atol=1e-7)
        policy=read('policy_backtest').reshape(nt,n)
        for k in range(nt):
            chosen=np.argmin(loss[:,:k].mean(1),axis=0) if k>=4 else np.zeros(n,int)
            np.testing.assert_allclose(policy[k],pred[chosen,k,np.arange(n)],atol=1e-7)
        # Check a real native-cell warming-only fit independently of the batch implementation.
        meta=json.loads((ROOT/'dist/data/metadata.json').read_text())['products'][product]
        years=np.array(meta['years']);values=np.fromfile(ROOT/f'dist/data/{product}_season_DJF.f32',dtype='<f4').reshape(len(years),n)
        # The DJF record starts one year after the first SST year, matching the case calendar.
        from forecast_index_models import certified_2025
        training=np.arange(2004 if product=='mur' else 1983,2026)
        outcome=np.vstack([values[np.searchsorted(years,training[:-1])],certified_2025(product,meta)])
        errors=[]
        for cell in np.unique(np.r_[0,n//2,n-1]):
            cut=max(10,np.quantile(outcome[:,cell],.8));labels=(outcome[:,cell]>cut).astype(float)
            if labels.min()==labels.max():expected=(labels.sum()+.5)/(len(labels)+1)
            else:expected=scalar(training[:,None],labels,np.array([2026]))
            errors.append(abs(expected-current[1,cell]))
        assert max(errors)<1e-6
        results[product]={'cells':n,'independentWarmingFits':len(errors),'maximumDifference':float(max(errors)),'chronologicalSelectionVerified':True}
    output={'passed':True,'independentSyntheticFits':18,'maximumFitDifference':float(max(abs(p-ref))),'products':results}
    (ROOT/'qa/outlook_combinations_validation.json').write_text(json.dumps(output,indent=2))
    print(json.dumps(output,indent=2))

if __name__=='__main__':main()
