"""Recheck photo-coordinate templates, including sexagesimal Commons locations."""
import json,re,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from expand_photo_library import CACHE,session,get,save,REJECT

def coordinate(content):
    match=re.search(r'\{\{((?:[Ll]ocation|[Oo]bject location)(?: dec)?)\s*\|([^{}]+)\}\}',content)
    if not match:return None
    parts=[p.strip() for p in match.group(2).split('|')]
    try:
        if len(parts)>=8 and parts[3].upper() in ('N','S') and parts[7].upper() in ('E','W'):
            lat=(float(parts[0])+float(parts[1])/60+float(parts[2])/3600)*(-1 if parts[3].upper()=='S' else 1)
            lon=(float(parts[4])+float(parts[5])/60+float(parts[6])/3600)*(-1 if parts[7].upper()=='W' else 1)
        elif len(parts)>=6 and parts[2].upper() in ('N','S') and parts[5].upper() in ('E','W'):
            lat=(float(parts[0])+float(parts[1])/60)*(-1 if parts[2].upper()=='S' else 1)
            lon=(float(parts[3])+float(parts[4])/60)*(-1 if parts[5].upper()=='W' else 1)
        elif len(parts)>=4 and parts[1].upper() in ('N','S') and parts[3].upper() in ('E','W'):
            lat=float(parts[0])*(-1 if parts[1].upper()=='S' else 1);lon=float(parts[2])*(-1 if parts[3].upper()=='W' else 1)
        else:lat,lon=float(parts[0]),float(parts[1])
    except (ValueError,IndexError):return None
    if not (-90<=lat<=90 and -180<=lon<=180):return None
    return {'latitude':lat,'longitude':lon,'coordinateTemplate':match.group(0),'locationPrecision':'Source coordinate' if match.group(1).lower().startswith('object') else 'GPS'}

def main():
    candidates=json.loads((CACHE/'candidates.json').read_text('utf8'))
    path=CACHE/'coordinate_audit.json';audited=json.loads(path.read_text('utf8')) if path.exists() else {}
    pending=[p for p in candidates if p['id'] not in audited and p['locationPrecision']=='GPS']
    s=session()
    for start in range(0,len(pending),35):
        group=pending[start:start+35];bytitle={p['sourceTitle']:p for p in group}
        response=get(s,'https://commons.wikimedia.org/w/api.php',params={'action':'query','format':'json','titles':'|'.join(bytitle),'prop':'revisions','rvprop':'content','rvslots':'main'}).json()
        for page in response.get('query',{}).get('pages',{}).values():
            p=bytitle.get(page['title'])
            if not p:continue
            content=page.get('revisions',[{}])[0].get('slots',{}).get('main',{}).get('*','')
            result=coordinate(content)
            audited[p['id']]=result or {'rejected':'No unambiguous coordinate template; do not present an inferred position as GPS.'}
        save(path,audited);print('AUDITED',len(audited),'of',len(pending),flush=True);time.sleep(.4)
    rejects=set(json.loads((CACHE/'manual_rejected.json').read_text('utf8')))
    for p in candidates:
        a=audited.get(p['id'])
        if not a:continue
        if 'rejected' in a:rejects.add(p['id']);continue
        lat,lon=a['latitude'],a['longitude']
        if p['basin']=='eastasia' and not (0<=lat<=55 and 110<=lon<=160):rejects.add(p['id'])
        elif p['basin']!='eastasia' and not (9<=lat<=32 and 31<=lon<=61):rejects.add(p['id'])
    save(CACHE/'manual_rejected.json',sorted(rejects))
    print('COORDINATES CHECKED',len(audited),'manual rejects',len(rejects),flush=True)
if __name__=='__main__':main()
