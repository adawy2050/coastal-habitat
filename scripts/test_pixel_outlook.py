"""Check batched point forecasts against independent single-point refits."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from update_climate import fit_probability,best_alpha,backtest

DATA=Path(__file__).resolve().parents[1]/'dist/data'
outlook=json.loads((DATA/'outlook.json').read_text());meta=json.loads((DATA/'metadata.json').read_text())
cases=pd.read_csv(DATA/'seasonal_training.csv')
checked=0;largest=0
for product,key in [('GHRSST MUR','mur'),('OISST','oisst')]:
    info=outlook['pixelOutlooks'][key];n=info['nativeCells'];years=meta['products'][key]['years'];season=info['season']
    source=np.fromfile(DATA/f'{key}_season_{season}.f32',dtype='<f4').reshape(len(years),n)
    template=next(t for t in outlook['targets'] if t['product']==product and t['scope']=='ecoregion')
    train=cases[(cases['product']==product)&(cases.season==season)&(cases.lead_months==info['leadMonths'])&
        (cases.habitat=='coral')&(cases.region=='Gulf of Aden')].sort_values('season_start_year').copy()
    positions=np.searchsorted(years,train.season_start_year.to_numpy())
    probabilities=np.fromfile(DATA/f'{key}_outlook_probability.f32',dtype='<f4')
    alpha_values=np.fromfile(DATA/f'{key}_outlook_alpha.f32',dtype='<f4')
    stored=np.fromfile(DATA/f'{key}_outlook_backtest_predictions.f32',dtype='<f4').reshape(len(info['testYears']),n)
    samples=np.unique(np.r_[np.linspace(0,n-1,22).astype(int),probabilities.argmin(),probabilities.argmax()])
    for cell in samples:
        point=train.copy();point['observed_mhw_days']=source[positions,cell];cache={}
        alpha=best_alpha(point,info['modes'],cache)
        assert np.isclose(alpha,alpha_values[cell]),(key,int(cell),alpha,alpha_values[cell])
        prediction=fit_probability(point,int(info['seasonStart'][:4]),[template['predictorValues'][m] for m in info['modes']],alpha,info['modes'])[0]
        difference=abs(prediction-probabilities[cell]);largest=max(largest,difference)
        assert difference<1e-6,(key,int(cell),difference)
        if checked%7==0:
            result=backtest(point,info['modes'],product,cache)
            reference=np.array([r['probability'] for r in result['predictions']])
            assert np.max(np.abs(reference-stored[:,cell]))<1e-6
        checked+=1
print(f'PASS: {checked} independent pixel refits; maximum probability difference {largest:.2g}; sampled nested backtests match.')
