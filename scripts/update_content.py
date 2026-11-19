"""Update dated source checks and the NOAA ENSO bulletin date.

News summaries and Arabic translations are curated in dist/content/news.json.
Add papers with complete bilingual metadata in papers.json; DOI identity and
publisher title are checked here. Failed sources retain their previous check.
No remote HTML or scripts are embedded in the site.
"""
from datetime import date, datetime, timedelta
import json
from pathlib import Path
import re
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]/'dist/content'


def get(url):
    with urlopen(Request(url,headers={'User-Agent':'HabitatMHWAtlas/1.0 (mailto:ahmed.eladawy@jamstec.go.jp)'}),timeout=35) as response:
        return response.read().decode('utf8')


def main():
    today=date.today().isoformat()
    news=json.loads((ROOT/'news.json').read_text(encoding='utf8'))
    bulletin=next(i for i in news['items'] if i['id']=='enso-discussion')
    html=get(bulletin['url'])
    match=re.search(r'\b(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+20\d\d)\b',re.sub('<[^>]+>',' ',html))
    if not match:raise ValueError('NOAA ENSO bulletin issue date was not found')
    bulletin['date']=datetime.strptime(match[1],'%d %B %Y').date().isoformat()
    assert bulletin['date']<=today
    bulletin['checked']=today;news['checked']=today
    (ROOT/'news.json').write_text(json.dumps(news,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    papers=json.loads((ROOT/'papers.json').read_text(encoding='utf8'))
    assert len({p['doi'].lower() for p in papers['items']})==len(papers['items'])
    for paper in papers['items']:
        assert paper['titleAr'] and paper['url']=='https://doi.org/'+paper['doi']
        if paper.get('verified','1900-01-01') < (date.today()-timedelta(days=90)).isoformat():
            metadata=json.loads(get('https://api.crossref.org/works/'+quote(paper['doi'],safe='')))['message']
            assert metadata['DOI'].lower()==paper['doi'].lower()
            assert metadata['title'][0].strip()==paper['title'].strip(), 'Publisher title changed; review its Arabic translation before updating.'
            paper['verified']=today
    papers['checked']=min(p['verified'] for p in papers['items'])
    (ROOT/'papers.json').write_text(json.dumps(papers,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    print('Source catalogue checked; ENSO bulletin',bulletin['date'])


if __name__=='__main__':main()
