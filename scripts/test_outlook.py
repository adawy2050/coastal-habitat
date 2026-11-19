"""Check saved seasonal estimates, complete-case leads and chronological scores."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.special import expit

DATA=Path(__file__).resolve().parents[1]/'dist/data'
outlook=json.loads((DATA/'outlook.json').read_text())
live=json.loads((DATA/'climate_latest.json').read_text())
training=pd.read_csv(DATA/'seasonal_training.csv')
targets=[t for t in outlook['targets'] if t['available']]
groups=json.loads((DATA/'seasonal_groups.json').read_text())
assert len(targets)==len(groups['groups'])*2
for target in targets:
    assert target['leadMonths'] in (1,2,3)
    assert target['modes']==['Nino34','NAO','AO','EAWR','NAtl_SSTA','PDO']
    assert all(live['latestByMode'][m]>=target['predictorLastMonth'] for m in target['modes'])
    issue=pd.Timestamp(target['issueDate'])
    assert target['predictorLastMonth']==str(issue.to_period('M')-2)
    assert pd.Timestamp(target['seasonStart'])==issue+pd.DateOffset(months=target['leadMonths'])
    train=training[(training['product']==target['product'])&(training.habitat==(target['habitat'] if target['scope']=='ecoregion' else 'coral'))&
        ((training.region==target['region']) if target['scope']=='ecoregion' else (training.region=='Gulf of Aden'))&(training.season==target['season'])&
        (training.lead_months==target['leadMonths'])&(pd.to_datetime(training.season_end)<issue)]
    if target['scope']=='overall':
        train=train.copy();key='mur' if target['product']=='GHRSST MUR' else 'oisst'
        j=next(i for i,g in enumerate(groups['groups']) if g['scope']=='overall' and g['habitat']==target['habitat'] and g.get('basin','redsea')==target.get('basin','redsea'))
        positions=np.searchsorted(groups['products'][key]['years'],train.season_start_year.to_numpy())
        train['observed_mhw_days']=np.array(groups['products'][key]['seasons'][target['season']],float)[positions,j]
    cut=max(10.,float(np.quantile(train.observed_mhw_days,.8)))
    assert abs(cut-target['highExposureThresholdDays'])<1e-10
    assert len(train)==target['trainingSeasons']
    assert train.season_start_year.max()<pd.Timestamp(target['seasonStart']).year
    model=target['model']
    x=np.array([target['predictorValues'][m] for m in target['modes']])
    time=np.array([1.,pd.Timestamp(target['seasonStart']).year-model['yearMean']])
    residual=x-time@np.array(model['climateTrend'])
    design=np.r_[1.,(residual-model['mean'])/np.array(model['scale'])]
    probability=float(expit(design@np.array(model['beta'])))
    assert abs(probability-target['probability'])<1e-12
    assert 0<=probability<=1 and 0<target['historicalProbability']<1
    for scope,score in target['backtest']['scores'].items():
        rows=[r for r in target['backtest']['predictions'] if scope=='all_retrospective' or r['baselineAvailable']]
        assert len(rows)==score['nTest']
        y=np.array([r['observedHigh'] for r in rows]);p=np.array([r['probability'] for r in rows]);b=np.array([r['baseline'] for r in rows])
        assert max(r['year'] for r in rows)<=target['trainingLastYear']
        skill=1-np.mean((y-p)**2)/np.mean((y-b)**2)
        assert abs(skill-score['skill'])<1e-12
    assert not target['validatedAlert']
print(f'PASS: {len(targets)} basin/habitat/ecoregion probabilities reproduced; feed dates, training-only cutoffs, leads and chronological backtests verified.')
