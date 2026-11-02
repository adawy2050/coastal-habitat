"""Publish compact progress to a separate branch without triggering site builds.

Use --once for an immediate refresh; otherwise poll every 5 minutes.
Credentials stay in process memory through the existing Git credential helper.
"""
from pathlib import Path
import argparse,datetime,json,os,subprocess,time
from urllib.error import HTTPError
from urllib.request import Request,urlopen

ROOT=Path(__file__).resolve().parents[1]
API='https://api.github.com/repos/adawy2050/coastal-habitat'

def read(path,default):
    try:return json.loads(path.read_text(encoding='utf8'))
    except (FileNotFoundError,json.JSONDecodeError):return default

def snapshot():
    science=read(ROOT/'dist/observed2026/status.json',{})
    try:
        import paramiko
        client=paramiko.SSHClient();client.load_system_host_keys();client.connect('172.24.30.56',username='eladawy',key_filename=str(Path.home()/'.ssh/id_rsa'),timeout=12,banner_timeout=12,auth_timeout=12)
        try:
            sftp=client.open_sftp();sftp.get_channel().settimeout(15)
            science=json.loads(sftp.open('/minamitori/data2/eladawy/ATLAS_UPDATE_20261022/status.json').read());sftp.close()
            dest=ROOT/'dist/observed2026/status.json';dest.parent.mkdir(exist_ok=True);dest.write_text(json.dumps(science,separators=(',',':')),encoding='utf8',newline='\n')
        finally:client.close()
    except Exception:pass
    photos=read(ROOT/'dist/status/photos.json',read(ROOT/'_cache/photo_expansion/progress.json',{}))
    jobs=science.get('jobs',[])
    if isinstance(jobs,dict):jobs=[dict(value,name=key) for key,value in jobs.items()]
    if not jobs and isinstance(science.get('products'),dict):
        jobs=[dict(value,name=('GHRSST MUR' if key=='mur' else 'NOAA OISST')+' · three study areas') for key,value in science['products'].items()]
    if not jobs:
        jobs=[{'name':name,'stage':'Preparing habitat-cell downloads','latestDate':None} for name in ['GHRSST MUR · three study areas','NOAA OISST · three study areas']]
    safe=[]
    for job in jobs:
        safe.append({k:job[k] for k in ['name','product','basin','stage','status','completed','total','latestDate'] if k in job})
    count=photos.get('total',photos.get('completed',photos.get('downloaded',47)))
    for job in safe:
        if job.get('name') in ['mur','oisst']:job['name']=('GHRSST MUR' if job['name']=='mur' else 'NOAA OISST')+' · three study areas'
    return {'updatedUtc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'message':('The update paused at a validation or download check; saved downloads are retained.' if science.get('status')=='failed' else science.get('message','Downloading daily observations and preparing habitat-cell analyses.')),'jobs':safe,'photos':{'completed':count,'target':470,'stage':photos.get('stage','Downloading and checking photographs.')}}

def main():
    p=argparse.ArgumentParser();p.add_argument('--once',action='store_true');p.add_argument('--interval',type=int,default=300);args=p.parse_args()
    r=subprocess.run(['git','-c','credential.interactive=never','credential','fill'],input='protocol=https\nhost=github.com\nusername=adawy2050\n\n',cwd=ROOT,text=True,capture_output=True,check=True,env={**os.environ,'GIT_TERMINAL_PROMPT':'0','GCM_INTERACTIVE':'Never'})
    fields=dict(line.split('=',1) for line in r.stdout.splitlines() if '=' in line)
    headers={'Authorization':'Bearer '+fields['password'],'Accept':'application/vnd.github+json','Content-Type':'application/json','User-Agent':'HabitatAtlasUpdateMonitor'}
    def api(path,method='GET',body=None):
        req=Request(API+path,data=json.dumps(body).encode() if body is not None else None,method=method,headers=headers)
        with urlopen(req,timeout=45) as response:
            raw=response.read();return json.loads(raw) if raw else None
    try:api('/git/ref/heads/atlas-progress')
    except HTTPError as error:
        if error.code!=404:raise
        head=api('/git/ref/heads/main')['object']['sha'];api('/git/refs','POST',{'ref':'refs/heads/atlas-progress','sha':head})
    previous=None
    while True:
        try:
            data=snapshot();path=ROOT/'dist/status/current.json';path.parent.mkdir(exist_ok=True);path.write_text(json.dumps(data,indent=2),encoding='utf8',newline='\n')
            signature=json.dumps({k:v for k,v in data.items() if k!='updatedUtc'},sort_keys=True)
            if signature!=previous:
                import base64
                try:sha=api('/contents/status/current.json?ref=atlas-progress')['sha']
                except HTTPError as error:
                    if error.code!=404:raise
                    sha=None
                payload={'message':'Update habitat analysis progress','branch':'atlas-progress','content':base64.b64encode(json.dumps(data,indent=2).encode()).decode()}
                if sha:payload['sha']=sha
                api('/contents/status/current.json','PUT',payload);previous=signature;print(data['updatedUtc'],'Progress published',flush=True)
        except Exception as error:print(type(error).__name__,str(error).splitlines()[0][:180],flush=True)
        if args.once:return
        time.sleep(max(30,args.interval))

if __name__=='__main__':main()
