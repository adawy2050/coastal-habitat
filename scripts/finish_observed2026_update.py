"""Wait for checked MUR results, sync, verify and publish the new data only.

The remote download supervisor is independent of this local publishing process.
Progress remains available while the dataset is being prepared.
"""
from pathlib import Path
import argparse,datetime,json,os,subprocess,sys,time
from urllib.request import Request,urlopen
from observed2026_sync import connection,REMOTE

ROOT=Path(__file__).resolve().parents[1]
API='https://api.github.com/repos/adawy2050/coastal-habitat'
ENV={**os.environ,'GIT_TERMINAL_PROMPT':'0','GCM_INTERACTIVE':'Never','PYTHONIOENCODING':'utf-8'}

def run(*args):
    subprocess.run(list(args),cwd=ROOT,env=ENV,check=True)

def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT,env=ENV,text=True).strip()

def deploy(sha):
    result=subprocess.run(['git','-c','credential.interactive=never','credential','fill'],input='protocol=https\nhost=github.com\nusername=adawy2050\n\n',cwd=ROOT,env=ENV,text=True,capture_output=True,check=True)
    fields=dict(line.split('=',1) for line in result.stdout.splitlines() if '=' in line)
    headers={'Authorization':'Bearer '+fields['password'],'Accept':'application/vnd.github+json','Content-Type':'application/json','User-Agent':'HabitatAtlasDataPublisher'}
    def api(path,method='GET'):
        with urlopen(Request(API+path,data=b'{}' if method=='POST' else None,headers=headers,method=method),timeout=60) as response:
            raw=response.read();return json.loads(raw) if raw else None
    for attempt in range(120):
        runs=api('/actions/workflows/pages.yml/runs?per_page=10')['workflow_runs'];matches=[r for r in runs if r['head_sha']==sha]
        if matches:
            job=matches[0]
            if job['status']=='completed':
                if job['conclusion']=='success':return job['html_url']
                if job.get('run_attempt',1)<3:
                    api('/actions/runs/'+str(job['id'])+'/rerun-failed-jobs','POST');time.sleep(20)
                else:raise RuntimeError('GitHub deployment failed after retries: '+job['html_url'])
        time.sleep(20)
    raise TimeoutError('GitHub deployment is still pending.')

def publish():
    assert git('branch','--show-current')=='main','Publish from the atlas main branch only.'
    assert git('remote','get-url','origin')=='https://github.com/adawy2050/coastal-habitat.git'
    staged=git('diff','--cached','--name-only');assert not staged,'Existing staged edits need review before automatic data publication.'
    run('git','fetch','origin');run('git','merge','--ff-only','origin/main')
    # The same science verifier used for the initial release checks every native cell.
    run(sys.executable,'scripts/observed2026_fetch.py')
    run(sys.executable,'scripts/observed2026_fetch.py','--verify-only')
    manifest=json.loads((ROOT/'dist/observed2026/manifest.json').read_text(encoding='utf8'))
    assert manifest['independentQCComplete'] and manifest['allProductsComplete']
    assert set(manifest['products'])=={'mur','oisst'}
    assert len(json.loads((ROOT/'dist/data/metadata.json').read_text(encoding='utf8'))['products']['mur']['cells'])==166771
    run(sys.executable,'scripts/observed2026_summaries.py')
    run(sys.executable,'scripts/forecast_index_models.py');run(sys.executable,'scripts/verify_forecast_indices.py')
    run(sys.executable,'scripts/build_assets.py');run(sys.executable,'scripts/verify_assets.py');run(sys.executable,'scripts/verify.py')
    total=sum(p.stat().st_size for p in (ROOT/'dist').rglob('*') if p.is_file());assert total<1024**3,'The site exceeds the GitHub Pages size budget.'
    run('git','add','dist/observed2026','dist/forecasts','dist/asset-manifest.json')
    allowed=git('diff','--cached','--name-only').splitlines();assert all(p.startswith(('dist/observed2026/','dist/forecasts/')) or p=='dist/asset-manifest.json' for p in allowed)
    if allowed:run('git','commit','-q','-m','Add checked 2026 MUR habitat observations for all study areas')
    sha=git('rev-parse','HEAD');run('git','push','origin','main');workflow=deploy(sha)
    result={'status':'deployed','updatedUtc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'commit':sha,'workflow':workflow,'url':'https://adawy2050.github.io/coastal-habitat/','products':list(manifest['products'])}
    target=ROOT/'_cache/observed2026/published.json';target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result),flush=True)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--interval',type=int,default=300);parser.add_argument('--max-hours',type=float,default=24);parser.add_argument('--check-only',action='store_true');args=parser.parse_args()
    deadline=time.monotonic()+args.max_hours*3600;previous=None
    while time.monotonic()<deadline:
        try:
            client=connection()
            try:sftp=client.open_sftp();sftp.get_channel().settimeout(20);status=json.loads(sftp.open(REMOTE+'/status.json').read());sftp.close()
            finally:client.close()
            current=(status.get('status'),status.get('products',{}).get('mur',{}).get('completed'))
            if current!=previous:print(datetime.datetime.now(datetime.timezone.utc).isoformat(),current,flush=True);previous=current
            if args.check_only:return
            if status.get('status')=='complete':publish();return
            if status.get('status')=='failed' and not status.get('retryable'):print('The server stopped at a check; progress page retains this state for review.',flush=True)
        except Exception as error:print(type(error).__name__,str(error).splitlines()[0][:220],flush=True)
        time.sleep(max(30,args.interval))
    raise TimeoutError('The update is still running; restart the local publisher to continue watching.')

if __name__=='__main__':main()
