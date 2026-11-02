"""Export completed kelp model outputs, never restricted environmental inputs.

Native daily outputs are reduced to calendar-month means and calendar-year
means/summed fluxes. Station-sized compressed uint16 display records keep the
combined Pages site small. The per-field rounding bound is stored in each file.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import argparse,gzip,hashlib,json,struct
import numpy as np
import pandas as pd
import xarray as xr

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'dist/kelp/data'
L=Path('D:/kep model/kelp_paper_revision_20260306/ssp_model_runs_20261020/manuscript_TPM20p43_20261021')
J=Path('D:/kep model/otherspeciesmodels/Saccharina_japonica_focus/32_Japonica_1931_model_ready_20261008/outputs_1991_2020_higher_mixedNO3')
FIELDS=['mass','density','standing','temperature_factor','light_factor','nitrogen_factor','joint_factor','growth','respiration','detachment','whole_loss','entry','tissue_loss','mortality','tissue_wear']
ANNUAL=FIELDS+['peak_mass','peak_standing']
FLUX={'growth','respiration','detachment','whole_loss','entry','tissue_loss'}
JCOL={'mass':'B_gDW_thallus','density':'mature_density_ind_m2','standing':'biomass_gDW_m2','temperature_factor':'fT','light_factor':'fI','nitrogen_factor':'fN','growth':'growth_gDW_m2_d','respiration':'respiration_gDW_m2_d','detachment':'erosion_gDW_m2_d','whole_loss':'whole_thallus_loss_gDW_m2_d','entry':'mature_entry_tissue_gDW_m2_d','tissue_loss':'seasonal_tissue_loss_gDW_m2_d','mortality':'mortality_d1','tissue_wear':'tissue_wear_fraction'}
LCOL={'mass':'B_daily_mean','temperature_factor':'fT_daily_mean','light_factor':'fI_daily_mean','nitrogen_factor':'fN_daily_mean','joint_factor':'JointGrowthFactor_daily_mean','growth':'DailyGrowth_DW','respiration':'DailyRespiration_DW','detachment':'DailyErosion_DW'}

def write_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(json.dumps(value,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8'))

def packed(a):
    valid=np.isfinite(a);assert np.all(a[valid]>=-1e-8)
    a=np.maximum(a,0);scale=np.nanmax(np.where(valid,a,0),axis=0)/65534
    scale=np.where(scale>0,scale,1.)
    q=np.where(valid,np.rint(np.nan_to_num(a)/scale),65535).astype('<u2')
    decoded=np.where(q==65535,np.nan,q.astype(float)*scale)
    err=np.abs(decoded-a);bound=np.broadcast_to(scale/2,a.shape)
    assert np.all(err[valid]<=bound[valid]+1e-9)
    return q,scale

def record(path,monthly,annual):
    q,s=packed(monthly);a,t=packed(annual)
    raw=struct.pack('<4I',len(monthly),len(annual),len(FIELDS),len(ANNUAL))+np.r_[s,t].astype('<f8').tobytes()+q.tobytes()+a.tobytes()
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(gzip.compress(raw,compresslevel=7,mtime=0))
    return hashlib.sha256(path.read_bytes()).hexdigest()

def aggregate(frame,peak=None):
    monthly=frame.groupby(frame.index.to_period('M')).mean().reindex(columns=FIELDS)
    annual=frame.groupby(frame.index.year).agg({c:'sum' if c in FLUX else 'mean' for c in frame}).reindex(columns=FIELDS)
    annual['peak_mass']=(peak if peak is not None else frame.mass).groupby(frame.index.year).max()
    annual['peak_standing']=frame.standing.groupby(frame.index.year).max() if 'standing' in frame else np.nan
    # Independently recompose annual mass and integrated flux from month means.
    days=monthly.index.days_in_month.to_numpy()
    for field in ['mass',*[f for f in FLUX if f in frame]]:
        grouped=(monthly[field]*days).groupby(monthly.index.year).sum()
        if field not in FLUX:grouped/=pd.Series(days,index=monthly.index.year).groupby(level=0).sum()
        np.testing.assert_allclose(grouped,annual[field],rtol=2e-12,atol=2e-8)
    return monthly.to_numpy(),annual.reindex(columns=ANNUAL).to_numpy()

def japonica_one(row):
    station=row.station_id;folder=J/station
    complete=json.loads((folder/'COMPLETE.json').read_text());assert complete['status']=='conditional_scenario_complete'
    metadata=json.loads((folder/'metadata.json').read_text());report=json.loads((folder/'report.json').read_text());assert report['spinup']['converged']
    dest=OUT/'japonica/historical'/f'{station}.bin.gz';receipt=ROOT/'_cache/kelp_export'/f'{station}.json'
    source=folder/'daily.csv';fingerprint=[source.stat().st_size,source.stat().st_mtime_ns]
    if dest.exists() and receipt.exists() and json.loads(receipt.read_text()).get('fingerprint')==fingerprint:
        return json.loads(receipt.read_text())['station']
    d=pd.read_csv(source,usecols=['date',*JCOL.values()],parse_dates=['date']).set_index('date').rename(columns={v:k for k,v in JCOL.items()})
    assert len(d)==10958 and d.index[0]==pd.Timestamp('1991-01-01') and d.index[-1]==pd.Timestamp('2020-12-31') and (d.index.to_series().diff().dropna()==pd.Timedelta(days=1)).all()
    assert np.isfinite(d.to_numpy()).all()
    np.testing.assert_allclose(d.standing,d.mass*d.density,rtol=2e-12,atol=2e-8)
    monthly,annual=aggregate(d)
    native=pd.read_csv(folder/'annual.csv')
    np.testing.assert_allclose(annual[:,ANNUAL.index('peak_mass')],native.mass_max,rtol=1e-12)
    np.testing.assert_allclose(annual[:,ANNUAL.index('peak_standing')],native.area_max,rtol=1e-12)
    digest=record(dest,monthly,annual)
    station_info={'id':station,'lat':float(metadata['latitude']),'lon':float(metadata['longitude']),'species':'japonica','group':'Japan','sourceDays':len(d),'meanMass':round(float(d.mass.mean()),5),'maxBudgetResidual':float(report['max_bed_budget_residual_gDW_m2']),'files':{'historical':f'japonica/historical/{station}.bin.gz'},'displaySha256':{'historical':digest}}
    write_json(receipt,{'fingerprint':fingerprint,'station':station_info})
    return station_info

def longissima():
    registry=pd.read_csv(L/'historical/stations_99.csv');result=[];series={};peaks={};hashes={}
    for scenario,paths in {'historical':[L/f'historical/kelp_output_{block}_corrected_Io180.nc' for block in ['1996_2000','2001_2020']],
        'ssp126':[L/'future/SSP126/results/outputs/kelp_SSP126_MI_99stations_2021_2100.nc'],
        'ssp585':[L/'future/SSP585/results/outputs/kelp_SSP585_MI_99stations_2021_2100.nc']}.items():
        frames=[];peak=[]
        for path in paths:
            with xr.open_dataset(path) as ds:
                name='time' if scenario=='historical' else 'day_time';dates=pd.DatetimeIndex(ds[name].values)
                ids=np.asarray(ds['station' if scenario=='historical' else 'station_id'])
                np.testing.assert_array_equal(ids,registry.segment_id)
                values={key:np.asarray(ds[value],float) for key,value in LCOL.items()}
                if scenario!='historical':
                    # Exact internal-step products are in the diagnostic replay.
                    with xr.open_dataset(L/f'future/limitation_diagnostics/{scenario.upper()}_limitation_diagnostics.nc') as diag:
                        np.testing.assert_array_equal(pd.DatetimeIndex(diag.day_time.values),dates)
                        values['joint_factor']=np.asarray(diag.joint_fT_fI_fN,float)
                frames.append((dates,values));peak.append(np.asarray(ds.B_daily_max,float))
        dates=frames[0][0].append([f[0] for f in frames[1:]])
        values={k:np.concatenate([f[1][k] for f in frames]) for k in LCOL};peak=np.concatenate(peak)
        assert len(dates)==len(pd.date_range(dates[0],dates[-1])) and dates.is_unique
        annual_native=pd.read_csv(L/'historical/annual_station_metrics_continuous.csv') if scenario=='historical' else None
        for i,row in registry.iterrows():
            frame=pd.DataFrame({k:v[:,i] for k,v in values.items()},index=dates)
            monthly,annual=aggregate(frame,pd.Series(peak[:,i],index=dates))
            if annual_native is not None:
                prior=annual_native[annual_native.station_id==row.segment_id].sort_values('year')
                np.testing.assert_allclose(annual[:,0],prior.B_annual_mean_gDW,rtol=1e-11)
                np.testing.assert_allclose(annual[:,ANNUAL.index('peak_mass')],prior.B_annual_peak_gDW,rtol=1e-11)
                np.testing.assert_allclose(annual[:,ANNUAL.index('detachment')],prior.annual_erosion_gDW,rtol=1e-11)
            sid=str(int(row.segment_id));dest=OUT/f'longissima/{scenario}/{sid}.bin.gz';digest=record(dest,monthly,annual)
            if scenario=='historical':result.append({'id':sid,'lat':float(row.lat),'lon':float(row.lon),'species':'longissima','group':{0:'G1 · Nemuro',1:'G2 · Hamanaka',2:'G3 · Kushiro'}[int(row.group_id)],'sourceDays':len(dates),'meanMass':round(float(frame.mass.mean()),5),'files':{},'displaySha256':{}})
            result[i]['files'][scenario]=f'longissima/{scenario}/{sid}.bin.gz';result[i]['displaySha256'][scenario]=digest
        print('Longissima',scenario,len(registry),'station records',flush=True)
    return result

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--workers',type=int,default=6);args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    stations=longissima();batch=pd.read_csv(J/'batch_status.csv');assert len(batch)==1930 and batch.status.eq('completed_conditional_scenario').all()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        jobs=[pool.submit(japonica_one,row) for row in batch.itertuples()]
        for k,job in enumerate(as_completed(jobs),1):
            stations.append(job.result())
            if k%100==0 or k==len(jobs):print('Japonica',k,'/',len(jobs),flush=True)
    stations.sort(key=lambda s:(s['species'],s['id']))
    manifest={'version':'20261102-kelp-r1','reviewed':'2026-11-02','monthlyFields':FIELDS,'annualFields':ANNUAL,
      'encoding':'gzip; 4 little-endian uint32 dimensions; float64 scales for monthly then annual fields; uint16 month-major then year-major values. 65535 is missing. Decode q*scale; absolute rounding error <= scale/2.',
      'aggregation':'Calendar-month means; calendar-year means for states/factors and sums for fluxes. Annual peaks use native internal-step maxima for longissima and native daily states for japonica.',
      'species':{'longissima':{'name':'Saccharina longissima','stations':99,'status':'Manuscript station simulations','monthlyAvailable':list(LCOL),'scenarios':{'historical':{'name':'Historical','firstMonth':'1996-01','lastMonth':'2020-12'},'ssp126':{'name':'SSP1-2.6','firstMonth':'2021-01','lastMonth':'2100-12'},'ssp585':{'name':'SSP5-8.5','firstMonth':'2021-01','lastMonth':'2100-12'}}},
      'japonica':{'name':'Saccharina japonica','stations':1930,'status':'Historical mature-bed scenario','monthlyAvailable':list(JCOL),'scenarios':{'historical':{'name':'Historical scenario','firstMonth':'1991-01','lastMonth':'2020-12'}}}},
      'stations':stations,
      'provenance':{'longissima':'Adopted TPM20.43 manuscript run; historical 1996–2020, SSP1-2.6 and SSP5-8.5 2021–2100. Future first five years are adjustment. Joint factors are means of internal-step products.',
      'japonica':'Completed 1,930-station higher-density mixed-NO3 delivery, October 2026; 1991–2020. One of 1,931 planned locations was blocked. 2019–2020 nitrate uses stored GFDL-ESM2M RCP2.6 in place of the JRA55-do archive.',
      'scope':'Processed model results only. No restricted forcing files, private manuscript links, monitoring records or unpublished manuscript PDFs are distributed.'}}
    write_json(OUT/'catalogue.json',manifest)
    audit={'passed':True,'stationCounts':{'longissima':99,'japonica':1930},'stationScenarioFiles':len(list(OUT.rglob('*.bin.gz'))),'sourceChecks':['complete native calendars','source station IDs and coordinates','native annual peaks','monthly-to-annual mass/flux reconciliation','japonica mass-times-density identity','per-field quantisation error bounds','source spin-up completion'],'publicBytes':sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())}
    write_json(OUT/'validation.json',audit);write_json(ROOT/'qa/kelp_data_export.json',audit);print(json.dumps(audit),flush=True)

if __name__=='__main__':main()
