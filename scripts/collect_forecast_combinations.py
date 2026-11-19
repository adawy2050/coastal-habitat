"""Archive all nine public SINTEX index feeds and IRI forecast families.

Current observations are never presented as historical issued forecasts.
The local archive remains reproducible with source hashes and retrieval dates.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, re
import numpy as np
import pandas as pd
import requests
from lxml import etree as ET
from external_index_forecasts import NS, iri_svg

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / '_cache/climate_forecasts'
OUT = ROOT / 'dist/forecasts/combinations'
INDICES = {'Nino34':'Niño-3.4','DMI':'Indian Ocean Dipole','EMI':'El Niño Modoki',
           'ATL3':'Atlantic Niño','SIOD':'Subtropical Indian Ocean Dipole',
           'SASD':'South Atlantic Subtropical Dipole','NNI':'Ningaloo Niño',
           'CNI':'California Niño','DNI':'Dakar Niño'}

def forecast_families(raw):
    """Read only explicitly labelled aggregate paths, matching original parser."""
    result = {}
    for label, key in [('COMBINED AVG','combined'),('DYN Average','dynamic'),('STAT Average','statistical')]:
        tree=ET.fromstring(raw, ET.XMLParser(resolve_entities=False,no_network=True))
        comments=tree.xpath('//s:g[starts-with(@id,"legend_")]//comment()',namespaces=NS)
        for c in comments:
            if c.text.strip()=='COMBINED AVG':c.text='unused aggregate'
            elif c.text.strip()==label:c.text='COMBINED AVG'
        if label=='COMBINED AVG':
            result[key]=iri_svg(raw)
        else:
            result[key]=iri_svg(ET.tostring(tree,encoding='utf-8'))
    return result

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    now=datetime.now(timezone.utc).isoformat()
    old=json.loads((ROOT/'dist/forecasts/iri_issue_archive.json').read_text())
    archive=[]
    for item in old:
        path=CACHE/f"IRI_{item['issueMonth'].replace('-','')}_figure.svg"
        if not path.exists():
            response=requests.get(item['source'],timeout=90);response.raise_for_status()
            assert hashlib.sha256(response.content).hexdigest()==item['sourceSha256'], 'Published archive changed; review before replacing a validated forecast input.'
            CACHE.mkdir(parents=True,exist_ok=True);path.write_bytes(response.content)
        raw=path.read_bytes()
        assert hashlib.sha256(raw).hexdigest()==item['sourceSha256']
        archive.append({**item,'families':forecast_families(raw)})
    (OUT/'iri_families.json').write_text(json.dumps(archive,indent=2),encoding='utf-8')
    result={'retrieved':now,'indices':{},'iriArchiveYears':len(archive),
            'iriIssueMonth':archive[-1]['issueMonth'],
            'source':'https://www.jamstec.go.jp/aplinfo/sintexf/e/seasonal/data_download.html',
            'archiveNote':'SINTEX CSVs contain observed history and current forecasts, not a historical forecast-issue archive. Old F1 image plots use a different model/baseline and are not substituted for current numeric hindcasts.',
            'iodArchive':'https://forecast.ccsr.columbia.edu/forecasts/iod?month=9&year=2025'}
    for key,label in INDICES.items():
        url=f'https://www.jamstec.go.jp/virtualearth/data/SINTEX/SINTEX_{key}.csv'
        response=requests.get(url,timeout=90);response.raise_for_status()
        raw=response.content;path=CACHE/f'SINTEX_{key}.csv';path.write_bytes(raw)
        frame=pd.read_csv(path)
        members=[c for c in frame if c not in ['time','Obs','Mean','F1-Mean','F2-Mean','F2-3DVAR-Mean']]
        forecast=frame[frame.Obs.isna() & frame[members].notna().any(axis=1)]
        a=forecast[members].to_numpy(float)
        assert len(forecast)>=6 and np.isfinite(a).any()
        obs=frame.loc[frame.Obs.notna()]
        result['indices'][key]={'label':label,'source':url,'sourceSha256':hashlib.sha256(raw).hexdigest(),
             'sourceLastModified':response.headers.get('Last-Modified'),'baseline':'1983–2015','units':'°C',
             'dates':forecast.time.tolist(),'mean':forecast.Mean.tolist(),
             'q10':np.nanquantile(a,.1,axis=1).tolist(),'q90':np.nanquantile(a,.9,axis=1).tolist(),
             'memberNames':members,'members':[[float(v) if np.isfinite(v) else None for v in row] for row in a.T],
             'observedDates':obs.time.tolist(),'observedValues':obs.Obs.tolist(),
             'eligibleForIssuedForecastBacktest':False,
             'reason':'No matched numeric historical issue archive in this feed.'}
        print(key,len(forecast),'forecast months',flush=True)
    (OUT/'available_indices.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':main()
