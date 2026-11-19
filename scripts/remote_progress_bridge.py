"""Mirror small public progress snapshots from the analysis server.

Reads a credential once from stdin, retains it only in process memory, and
detaches. No credentials are written to files, URLs, arguments or logs.
"""
import base64,datetime,json,os,sys,time
from pathlib import Path
from urllib.request import Request,urlopen

def main():
    secret=json.loads(sys.stdin.readline());token=secret.pop('token');root=Path(secret['root']);photo=secret['photos']
    pid=os.fork()
    if pid:print('Progress bridge PID',pid,flush=True);return
    os.setsid();null=os.open('/dev/null',os.O_RDONLY);log=os.open(str(root/'github_progress.log'),os.O_WRONLY|os.O_CREAT|os.O_APPEND,0o600);os.dup2(null,0);os.dup2(log,1);os.dup2(log,2);os.closerange(3,256)
    (root/'github_progress.pid').write_text(str(os.getpid()))
    base='https://api.github.com/repos/adawy2050/coastal-habitat';headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','Content-Type':'application/json','User-Agent':'HabitatAtlasProgressBridge'}
    def api(path,body=None):
        req=Request(base+path,data=json.dumps(body).encode() if body is not None else None,headers=headers,method='PUT' if body is not None else 'GET')
        with urlopen(req,timeout=45) as response:return json.load(response)
    previous=None
    for tick in range(7*24*12):
        try:
            if (root/'photo_progress.json').exists():photo=json.loads((root/'photo_progress.json').read_text())
            status=json.loads((root/'status.json').read_text());ready={}
            if (root/'public/manifest.json').exists():ready=json.loads((root/'public/manifest.json').read_text()).get('products',{})
            jobs=[]
            for name,row in status.get('products',{}).items():
                jobs.append({'name':('GHRSST MUR' if name=='mur' else 'NOAA OISST')+' · three study areas','stage':'Analysis checked' if name in ready else row.get('status','preparing'),'completed':row.get('completed',0),'total':row.get('total',0),'latestDate':row.get('latestDate')})
            message='Observed 2026 SST and heatwave analysis are in progress.'
            if 'oisst' in ready:message='OISST observations are ready for all three regions. The MUR update is continuing.'
            if status.get('status')=='failed':message='The update paused at a check. Downloaded data are retained.'
            published=False
            if 'mur' in ready:
                message='Both analyses are checked. The website update is being prepared.'
                if (root/'release_status.json').exists():
                    release=json.loads((root/'release_status.json').read_text());stage=release.get('stage','')
                    if stage=='Publication retry':message='Both analyses are checked. Website publication is retrying; the last published version remains available.'
                    elif stage=='Publication needs review':message='Both analyses are checked. Website publication needs review.'
                    elif stage in ['Confirming cross-year events','Preparing publication','Checking data and cell models','Deploying']:message='Both analyses are checked. '+stage+'.'
                try:
                    with urlopen('https://adawy2050.github.io/coastal-habitat/observed2026/manifest.json?t='+str(int(time.time())),timeout=30) as response:live=json.load(response)
                    published='mur' in live.get('products',{})
                except Exception:pass
                if published:message='The 2026 MUR and OISST observations are available in the atlas for all three regions.'
            payload={'updatedUtc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'message':message,'jobs':jobs,'photos':photo}
            signature=json.dumps({k:v for k,v in payload.items() if k!='updatedUtc'},sort_keys=True)
            if signature!=previous or tick%6==0:
                current=api('/contents/status/current.json?ref=atlas-progress')
                api('/contents/status/current.json',{'message':'Update habitat analysis progress','branch':'atlas-progress','sha':current['sha'],'content':base64.b64encode(json.dumps(payload,indent=2).encode()).decode()});previous=signature;print(payload['updatedUtc'],message,flush=True)
            if published:break
        except Exception as error:print(type(error).__name__,str(error).splitlines()[0][:150],flush=True)
        time.sleep(300)

if __name__=='__main__':main()
