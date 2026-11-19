"""Archive forecasts issued by other centres; never substitute observed futures.

IRI's public SVGs retain the plotted numerical vertices and labelled axes.
Recover their published COMBINED AVG to 0.01 degC, rather than attempting to
access the restricted raw-data service. Save source hashes and fail closed if
the figure layout/labels change. JAMSTEC's public CSV is used without tracing.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, re, time
import numpy as np
import pandas as pd
import requests
from lxml import etree as ET

ROOT=Path(__file__).resolve().parents[1]
CACHE=ROOT/'_cache/climate_forecasts'
OUT=ROOT/'dist/forecasts'
NS={'s':'http://www.w3.org/2000/svg'}

def iri_svg(raw):
    tree=ET.fromstring(raw,ET.XMLParser(resolve_entities=False,no_network=True))
    ticks={}
    for axis in ['x','y']:
        values=[]
        for g in tree.xpath(f'//s:g[starts-with(@id,"{axis}tick_")]',namespaces=NS):
            label=g.xpath('.//comment()')[0].text.strip()
            p=g.xpath('.//s:path[@clip-path]/@d',namespaces=NS)[0]
            xy=[float(n) for n in re.findall(r'-?\d+(?:\.\d+)?',p)]
            values.append((xy[0 if axis=='x' else 1],label))
        ticks[axis]=values
    ys=np.array([[a,float(b.replace('\u2212','-'))] for a,b in ticks['y']])
    slope,intercept=np.polyfit(ys[:,0],ys[:,1],1)
    assert np.max(np.abs(ys[:,0]*slope+intercept-ys[:,1]))<1e-5
    legend=tree.xpath('//s:g[starts-with(@id,"legend_")]',namespaces=NS)[0]
    matches=[]
    for g in legend:
        comments=g.xpath('.//comment()')
        if comments and comments[0].text.strip()=='COMBINED AVG':
            matches=g.getprevious().xpath('.//s:path/@style',namespaces=NS)
    assert len(matches)==1,'Missing/ambiguous published combined average'
    paths=tree.xpath('//s:path[@clip-path and @style=$style]',style=matches[0],namespaces=NS)
    assert len(paths)==1,'Missing/ambiguous data curve'
    path=paths[0].get('d');assert not re.search('[a-zAC-HJ-KN-Z]',path)
    coords=np.array([float(v) for v in re.findall(r'-?\d+(?:\.\d+)?',path)]).reshape(-1,2)
    data={}
    for x,y in coords:
        pos,label=min(ticks['x'],key=lambda t:abs(t[0]-x))
        assert abs(x-pos)<.001
        if 'OBS' not in label:data[label]=round(float(y*slope+intercept),2)
    assert len(data)>=6 and all(abs(v)<8 for v in data.values())
    return data

def main():
    CACHE.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
    now=datetime.now(timezone.utc);session=requests.Session()
    session.headers['User-Agent']='CoastalHabitatAtlas/1.0 (public published forecasts)'
    outlook=json.loads((ROOT/'dist/data/outlook.json').read_text());model_issue=next(iter(outlook['pixelOutlooks'].values()))['issueDate'];month=int(model_issue[5:7])
    archives=[]
    # Match the operational issue month, rather than using a different lead.
    for year in range(2004,now.year+1):
        file=CACHE/f'IRI_{year}{month:02d}_figure.svg'
        url=f'https://ensoforecast.iri.columbia.edu/figure4_plot/{year}/{month}'
        if not file.exists():
            response=session.get(url,timeout=90)
            if response.status_code==404 and year==now.year:break
            response.raise_for_status()
            assert 'svg' in response.headers.get('Content-Type','')
            file.write_bytes(response.content);time.sleep(.3)
        raw=file.read_bytes();values=iri_svg(raw)
        archives.append({'issueMonth':f'{year}-{month:02d}','index':'Nino34','units':'degC',
            'provider':'Columbia/IRI','series':'Published combined model average',
            'seasons':values,'source':url,'sourceSha256':hashlib.sha256(raw).hexdigest(),
            'extraction':'Published SVG axis and curve vertices; rounded to 0.01 degC'})
        print(year,list(values.items())[:2],flush=True)
    published=archives[-1]
    page=session.get('https://forecast.ccsr.columbia.edu/forecasts/enso/plumes',timeout=90);page.raise_for_status()
    match=re.search(r'var ISSUANCES = (\[.*?\]);',page.text)
    if match:
        released=[v for v in json.loads(match[1]) if not v.get('unreleased') and (v['year'],v['month'])<=(now.year,now.month)]
        current=max(released,key=lambda v:(v['year'],v['month']))
        label=f"{current['year']}-{current['month']:02d}"
        if label!=published['issueMonth']:
            url=f"https://ensoforecast.iri.columbia.edu/figure4_plot/{current['year']}/{current['month']}"
            r=session.get(url,timeout=90);r.raise_for_status();values=iri_svg(r.content)
            published={**published,'issueMonth':label,'seasons':values,'source':url,'sourceSha256':hashlib.sha256(r.content).hexdigest()}
    latest={'retrieved':now.isoformat(),'iri':published,'jamstec':{},
        'methodology':'https://www.jamstec.go.jp/aplinfo/sintexf/e/seasonal/data_download.html'}
    for index in ['Nino34','DMI']:
        url=f'https://www.jamstec.go.jp/virtualearth/data/SINTEX/SINTEX_{index}.csv'
        response=session.get(url,timeout=90);response.raise_for_status()
        file=CACHE/f'SINTEX_{index}.csv';file.write_bytes(response.content)
        df=pd.read_csv(file)
        member_columns=[c for c in df if c not in ['time','Obs','Mean','F1-Mean','F2-Mean','F2-3DVAR-Mean']]
        # The boundary observation can also occupy Mean. Only rows with actual
        # forecast members are forecasts; retain missing months as gaps.
        forecast=df[df.Obs.isna() & df[member_columns].notna().any(axis=1)].copy()
        members=forecast[member_columns].to_numpy(float)
        assert 9<=len(forecast)<=12 and np.isfinite(members).sum()>100
        latest['jamstec'][index]={'provider':'JAMSTEC SINTEX-F','source':url,
            'sourceLastModified':response.headers.get('Last-Modified'),
            'sourceSha256':hashlib.sha256(response.content).hexdigest(),'units':'degC',
            'baseline':'1983–2015','dates':forecast.time.tolist(),
            'observedDates':df.loc[df.Obs.notna(),'time'].tail(24).tolist(),
            'observedValues':df.loc[df.Obs.notna(),'Obs'].tail(24).tolist(),
            'mean':forecast.Mean.tolist(),
            'q10':np.nanquantile(members,.1,axis=1).tolist(),
            'q90':np.nanquantile(members,.9,axis=1).tolist(),
            'members':[[float(v) if np.isfinite(v) else None for v in row] for row in members.T],
            'note':'Ensemble percentiles describe model spread, not calibrated confidence intervals.'}
    (OUT/'index_forecasts.json').write_text(json.dumps(latest,ensure_ascii=False,indent=2),encoding='utf8')
    (OUT/'iri_issue_archive.json').write_text(json.dumps(archives,indent=2),encoding='utf8')
    print('Saved externally issued index forecasts and October archive.',flush=True)

if __name__=='__main__':main()
