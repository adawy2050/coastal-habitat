"""Add polygon stocks and annual erosion, preserving the adopted spatial weights.

Japonica polygons are dissolved MOE coverage patches, avoiding duplicate survey
overlaps. Stocks are annual mean standing mass; erosion is a yearly flux.
"""
from pathlib import Path
import gzip,json
import numpy as np
import pandas as pd
import geopandas as gpd
import netCDF4
from scipy.sparse import coo_matrix
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'dist/kelp/data/spatial'
LONG=Path('D:/kep model/kelp_paper_revision_20260306')
JAP=Path('D:/kep model/otherspeciesmodels/Saccharina_japonica_focus/daily_export_package_1930stations_2km_MOE_supported_1991_2020/metadata')
def write(species,x):
 (OUT/(species+'.json.gz')).write_bytes(gzip.compress(json.dumps(x,separators=(',',':'),allow_nan=False).encode(),mtime=0))
def main():
 audit={}
 for species in ['longissima','japonica']:
  print('Building',species,flush=True);x=json.loads(gzip.decompress((OUT/(species+'.json.gz')).read_bytes()));years=x['years']
  if species=='longissima':
   m=LONG/'daily_export_package_99stations_2km_1991_2020/metadata';p=LONG/'ssp_model_runs_20261020/manuscript_TPM20p43_20261021';accepted=pd.read_csv(m/'accepted_polygon_metadata.csv');links=pd.read_csv(m/'polygon_to_2km_grid_intersections.csv')
   attrs=gpd.read_file('D:/kep model/ministry distribution/shapefiles/mo4_alla_M_D_joinT_addField_v2.shp',columns=['FIRST_ID','div_KB'],ignore_geometry=True)
   reported=pd.Series(pd.to_numeric(attrs.div_KB).to_numpy()*1e4,index=pd.to_numeric(attrs.FIRST_ID));accepted['area']=accepted.polygon_id.map(reported)
   ids=pd.read_csv(p/'paper_stations.csv').segment_id.tolist();erosion=[];stock=[];peaks=[]
   for block in ['1996_2000','2001_2020']:
    with netCDF4.Dataset(p/f'historical/kelp_output_{block}_corrected_Io180.nc') as d:
     np.testing.assert_array_equal(ids,d['station'][:]);t=d['time'];yy=np.array([v.year for v in netCDF4.num2date(t[:],t.units,t.calendar)])
     e=np.asarray(d['DailyErosion_DW'][:]);b=np.asarray(d['B_daily_mean'][:]);peak=np.asarray(d['B_daily_max'][:])
     for y in np.unique(yy):erosion.append(e[yy==y].sum(axis=0));stock.append(b[yy==y].mean(axis=0));peaks.append(peak[yy==y].max(axis=0))
   peaks=np.array(peaks);density=np.full(len(ids),12.);rows=[];ref=np.median(peaks[:5],axis=0)
   for i in range(len(years)):
    if i>=5:
     survivors=.85*np.exp(-2*np.maximum(0,1-peaks[i-1]/ref))*density;density=np.minimum(15,survivors+2*np.maximum(0,1-survivors/15))
    rows.append(density.copy())
   native={'erosion':np.array(erosion)*rows,'standing':np.array(stock)*rows};polygons=accepted.polygon_id.astype(str).tolist();weights=accepted.assign(station=accepted.assigned_station_id.astype(str),polygon=accepted.polygon_id.astype(str)).rename(columns={'area':'weight'});ids=list(map(str,ids))
   links['weight']=links.intersection_area_m2*links.polygon_id.map(accepted.set_index('polygon_id')['area']/accepted.set_index('polygon_id').polygon_area_m2)
   gridweights=links.assign(station=links.assigned_station_id.astype(str),polygon=links.grid_2km_id)
   ix={s:i for i,s in enumerate(ids)};gx={g:i for i,g in enumerate(x['records'])};w=coo_matrix((gridweights.weight,([gx[g] for g in gridweights.polygon],[ix[s] for s in gridweights.station])),shape=(len(gx),len(ids))).tocsr()
   gs=np.asarray((w@native['standing'].T).T)
   for i,g in enumerate(gx):x['records'][g]['series']['standing']=np.round(gs[:,i],3).tolist()
   x['regional']['standing']=np.round(gs.sum(axis=1),3).tolist()
   geometry=x['coverage'];x['polygonNote']='Original accepted MOE konbu polygon. Annual mean standing stock and yearly erosion use the revised historical model and the same adopted density and div_KB area weights as the 2 km totals.'
  else:
   links=pd.read_csv(JAP/'polygon_to_2km_grid_intersections.csv');weights=links.groupby(['polygon_id','assigned_station_id'],as_index=False).intersection_area_m2.sum().rename(columns={'polygon_id':'polygon','assigned_station_id':'station','intersection_area_m2':'weight'})
   ids=sorted(weights.station.unique());polygons=sorted(weights.polygon.unique());flux=pd.read_csv(JAP/'station_annual_flux_sums.csv');native={k:flux.pivot(index='year',columns='station_id',values=v).reindex(index=years,columns=ids).to_numpy() for k,v in [('erosion','daily_export_gDW_m2'),('whole_loss','daily_whole_thallus_loss_gDW_m2'),('total_detached','daily_total_detached_gDW_m2')]}
   monthly=pd.read_csv(JAP/'station_monthly_summary.csv',usecols=['month','station_id','standing_biomass_gDW_m2','calendar_days']);monthly['year']=monthly.month.str[:4].astype(int);monthly['integral']=monthly.standing_biomass_gDW_m2*monthly.calendar_days
   annual=monthly.groupby(['year','station_id']).agg(integral=('integral','sum'),days=('calendar_days','sum'));annual['standing']=annual.integral/annual.days;native['standing']=annual.standing.unstack('station_id').reindex(index=years,columns=ids).to_numpy()
   print('Reading and joining MOE coverage fragments',flush=True)
   fragments=gpd.read_file(JAP/'Japonica_delivery_spatial.gpkg',layer='habitat_fragments_2km',columns=['polygon_id']).to_crs(32655);fragments.geometry=fragments.geometry.simplify(15,preserve_topology=True)
   patches=fragments.dissolve(by='polygon_id').reset_index();geometry=json.loads(patches.to_crs(4326).to_json(drop_id=True));x['polygonNote']='Dissolved MOE survey-union patch, allocated across completed Japonica stations. Overlapping survey generations are not counted twice. This is mixed-species candidate habitat, not confirmed exclusive Japonica cover.'
  ix={s:i for i,s in enumerate(ids)};px={g:i for i,g in enumerate(polygons)};w=coo_matrix((weights.weight,([px[str(g)] for g in weights.polygon],[ix[str(s)] for s in weights.station])),shape=(len(px),len(ix))).tocsr();matrices={k:np.asarray((w@a.T).T) for k,a in native.items()};areas=np.asarray(w.sum(axis=1)).ravel()
  for k,a in matrices.items():np.testing.assert_allclose(a.sum(axis=1),x['regional'][k],rtol=1e-9,atol=.1)
  x['polygons']={g:{'areaM2':float(areas[i]),'stations':[ids[j] for j in w.getrow(i).indices],'series':{k:np.round(a[:,i],3).tolist() for k,a in matrices.items()}} for g,i in px.items()}
  for f in geometry['features']:f['properties']['polygon_id']=str(f['properties']['polygon_id'])
  x['version']='20261102-polygons-r1';x['coverage']=geometry;x['standingDefinition']='Annual mean standing biomass, tonnes DW; erosion is an annual flux, tonnes DW/year.';write(species,x)
  audit[species]={'polygons':len(px),'stockAndErosionConserved':True,'areaM2':float(areas.sum()),'years':[years[0],years[-1]]};print(audit[species],flush=True)
 (ROOT/'qa/kelp_polygon_export.json').write_text(json.dumps(audit,indent=2))
if __name__=='__main__':main()
