"""Publish MOE display geometry and native historical 2 km erosion totals.

Japonica retains the completed delivery. Longissima uses revised historical
native daily erosion and the adopted previous-year-peak density recurrence;
accepted geometric fragments are scaled to each manuscript div_KB area.
"""
from pathlib import Path
import gzip,json,hashlib
import numpy as np
import pandas as pd
import geopandas as gpd
import netCDF4
from shapely.geometry import box
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'dist/kelp/data/spatial'
LONG=Path('D:/kep model/kelp_paper_revision_20260306')
JAP=Path('D:/kep model/otherspeciesmodels/Saccharina_japonica_focus/daily_export_package_1930stations_2km_MOE_supported_1991_2020/metadata')
def save(name,value):
 raw=json.dumps(value,separators=(',',':'),allow_nan=False).encode();(OUT/name).write_bytes(gzip.compress(raw,mtime=0))
def geo(frame,columns):
 f=frame[columns+['geometry']].copy();f.geometry=f.geometry.simplify(15,preserve_topology=True);return json.loads(f.to_crs(4326).to_json(drop_id=True))
def main():
 OUT.mkdir(parents=True,exist_ok=True);audit={}
 for species in ['longissima','japonica']:
  if species=='japonica':
   coverage=gpd.read_file(JAP/'Japonica_delivery_spatial.gpkg',layer='combined_coverage').to_crs(32655)
   grids=gpd.read_file(JAP/'Japonica_delivery_spatial.gpkg',layer='grid_2km').to_crs(32655)
   meta=pd.read_csv(JAP/'grid_2km_metadata.csv');annual=pd.read_csv(JAP/'grid_2km_annual_summary.csv');years=sorted(annual.year.unique().tolist())
   fields={'erosion':'daily_export_gDW_grid_total','whole_loss':'daily_whole_thallus_loss_gDW_grid_total','total_detached':'daily_total_detached_gDW_grid_total','standing':'standing_biomass_gDW_grid_total_annual_mean'}
   matrices={k:annual.pivot(index='year',columns='grid_2km_id',values=v).reindex(index=years,columns=meta.grid_2km_id).to_numpy() for k,v in fields.items()}
   reference=pd.read_csv(JAP/'regional_annual_totals.csv').set_index('year')
   for k,column in [('erosion','region_erosion_gDW'),('whole_loss','region_whole_loss_gDW'),('total_detached','region_total_detached_gDW')]:np.testing.assert_allclose(matrices[k].sum(axis=1),reference.loc[years,column],rtol=1e-12)
   area=meta.covered_kelp_area_m2.to_numpy();note='MOE mixed-species candidate coverage within 5 km of completed occurrences; whole qualifying polygons retained. Static survey union, not annual or exclusive Japonica cover. Native completed historical delivery; erosion excludes whole-thallus loss. Areas are geodesic fragment areas.'
   source_count=10139
  else:
   m=LONG/'daily_export_package_99stations_2km_1991_2020/metadata';accepted=pd.read_csv(m/'accepted_polygon_metadata.csv');meta=pd.read_csv(m/'grid_2km_metadata.csv');links=pd.read_csv(m/'polygon_to_2km_grid_intersections.csv')
   coverage=gpd.read_file('D:/kep model/ministry distribution/shapefiles/mo4_alla_M_D_joinT_addField_v2.shp').to_crs(32655)
   coverage['polygon_id']=pd.to_numeric(coverage.FIRST_ID);coverage=coverage.set_index('polygon_id').loc[accepted.polygon_id].reset_index();coverage['assigned_station_id']=accepted.assigned_station_id.to_numpy()
   reported=pd.Series(pd.to_numeric(coverage.div_KB).to_numpy()*1e4,index=accepted.polygon_id)
   assert np.isclose(reported.sum()/1e4,2739.221537484233)
   links['weight']=links.intersection_area_m2*links.polygon_id.map(reported/accepted.set_index('polygon_id').polygon_area_m2)
   ids=pd.read_csv(LONG/'ssp_model_runs_20261020/manuscript_TPM20p43_20261021/paper_stations.csv').segment_id.to_numpy();years=list(range(1996,2021));erosion=[];peaks=[]
   for block in ['1996_2000','2001_2020']:
    with netCDF4.Dataset(LONG/f'ssp_model_runs_20261020/manuscript_TPM20p43_20261021/historical/kelp_output_{block}_corrected_Io180.nc') as d:
     np.testing.assert_array_equal(ids,d['station'][:]);t=d['time'];yy=np.array([v.year for v in netCDF4.num2date(t[:],t.units,t.calendar)])
     e=np.asarray(d['DailyErosion_DW'][:]);b=np.asarray(d['B_daily_max'][:])
     for y in np.unique(yy):erosion.append(e[yy==y].sum(axis=0));peaks.append(b[yy==y].max(axis=0))
   peaks=np.array(peaks);density=np.full(len(ids),12.);density_rows=[];reference=np.median(peaks[:5],axis=0)
   for i,y in enumerate(years):
    if i>=5:
     survivors=.85*np.exp(-2*np.maximum(0,1-peaks[i-1]/reference))*density;density=np.minimum(15,survivors+2*np.maximum(0,1-survivors/15))
    density_rows.append(density.copy())
   weights=links.pivot_table(index='grid_2km_id',columns='assigned_station_id',values='weight',aggfunc='sum',fill_value=0).reindex(index=meta.grid_2km_id,columns=ids,fill_value=0).to_numpy();area=weights.sum(axis=1)
   matrices={'erosion':(np.array(erosion)*np.array(density_rows))@weights.T};source_count=60
   np.testing.assert_allclose(matrices['erosion'].sum(axis=1),(np.array(erosion)*np.array(density_rows))@weights.sum(axis=0),rtol=1e-12)
   grids=gpd.GeoDataFrame(meta,geometry=[box(r.grid_min_easting_m,r.grid_min_northing_m,r.grid_max_easting_m,r.grid_max_northing_m) for r in meta.itertuples()],crs=32655)
   note='60 accepted MOE konbu polygons; original nearest-centroid station assignment within 12 km. Revised 1996–2020 model; K=15 thalli/m², 1996–2000 density=12, thereafter previous-year peak recurrence. Geometric fragment fractions scale manuscript div_KB areas. Erosion is local detached tissue, not transport or sequestration.'
  grid_ids=meta.grid_2km_id.tolist();grids=grids.set_index('grid_2km_id').loc[grid_ids].reset_index();grids['area_m2']=area
  records={str(g):{'areaM2':float(area[i]),'stations':str(meta.iloc[i].assigned_or_contributing_station_ids).split(';'),'series':{k:[round(float(v),3) for v in a[:,i]] for k,a in matrices.items()}} for i,g in enumerate(grid_ids)}
  save(species+'.json.gz',{'species':species,'years':years,'displayUnits':'tonnes DW per year; standing stock is annual mean tonnes DW','note':note,'coverage':geo(coverage,[] if species=='japonica' else ['polygon_id','assigned_station_id']),'grids':geo(grids,['grid_2km_id','area_m2']),'records':records,'regional':{k:[round(float(v),3) for v in a.sum(axis=1)] for k,a in matrices.items()},'valuesUnit':'g DW','sourcePolygonCount':source_count})
  audit[species]={'grids':len(grids),'sourcePolygons':source_count,'areaM2':float(area.sum()),'years':[years[0],years[-1]],'regionalConservation':True}
 (ROOT/'qa/kelp_spatial_export.json').write_text(json.dumps(audit,indent=2));print(json.dumps(audit,indent=2))
if __name__=='__main__':main()
