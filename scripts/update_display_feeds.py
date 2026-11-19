"""Refresh genuine daily AO/NAO display observations, separate from model inputs."""
from datetime import date, datetime, timezone
import csv
import io
import json
from pathlib import Path
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]/'dist/detail'
SOURCES={'AO':'https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.cdas.z1000.19500101_current.csv','NAO':'https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.nao.cdas.z500.19500101_current.csv'}


def main():
    rows={}
    today=date.today()
    for mode,url in SOURCES.items():
        with urlopen(Request(url,headers={'User-Agent':'HabitatMHWAtlas/1.0'}),timeout=60) as response:
            raw=response.read().decode('utf8')
        values={}
        for fields in list(csv.reader(io.StringIO(raw)))[1:]:
            if len(fields)!=4:continue
            try:
                day=date(*map(int,fields[:3]));value=float(fields[3])
            except ValueError:continue
            if date(1980,1,1)<=day<today and abs(value)<90:values[day.isoformat()]=value
        assert len(values)>10000
        rows[mode]={'dates':sorted(values),'values':[values[d] for d in sorted(values)],'source':url,'latest':max(values),'units':'NOAA daily standardised index','note':'Daily and monthly NOAA products retain their original normalisations. Daily data are display-only and are not substituted into the published annual or seasonal model.'}
    ROOT.mkdir(exist_ok=True)
    out={'checkedUtc':datetime.now(timezone.utc).isoformat(),'modes':rows,'observed':True}
    target=ROOT/'climate_daily.json';tmp=target.with_suffix('.tmp');tmp.write_text(json.dumps(out,separators=(',',':')));tmp.replace(target)
    print('Daily indices:',{m:v['latest'] for m,v in rows.items()})


if __name__=='__main__':main()
