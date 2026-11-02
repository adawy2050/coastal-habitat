"""Publish certified server outputs after completion, independently of the PC.

The existing GitHub sign-in is passed once on encrypted SSH stdin, retained in
memory, and supplied to Git in its process environment. Never write credentials
to disk, command arguments, the clone URL or logs. Writes stay under --root.
"""
from pathlib import Path
import argparse,base64,datetime,hashlib,json,os,shutil,subprocess,sys,time,traceback
import requests

REPO='https://github.com/adawy2050/coastal-habitat.git'
API='https://api.github.com/repos/adawy2050/coastal-habitat'

def main():
    a=argparse.ArgumentParser();a.add_argument('--root',type=Path,required=True);a.add_argument('--daemon',action='store_true');args=a.parse_args();root=args.root.resolve()
    assert root==Path('/minamitori/data2/eladawy/ATLAS_UPDATE_20261022')
    token=sys.stdin.readline().strip();assert token
    auth=base64.b64encode(('x-access-token:'+token).encode()).decode()
    if args.daemon:
        pid=os.fork()
        if pid:print(pid,flush=True);return
        os.setsid();log=os.open(root/'github_release.log',os.O_WRONLY|os.O_CREAT|os.O_APPEND,0o600);null=os.open('/dev/null',os.O_RDONLY)
        os.dup2(null,0);os.dup2(log,1);os.dup2(log,2)
        os.closerange(3,256)
    (root/'github_release.pid').write_text(str(os.getpid()))
    env={**os.environ,'GIT_TERMINAL_PROMPT':'0','GIT_CONFIG_COUNT':'1','GIT_CONFIG_KEY_0':'http.https://github.com/.extraheader','GIT_CONFIG_VALUE_0':'AUTHORIZATION: basic '+auth}
    py=root/'release-env/bin/python';headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','User-Agent':'CoastalHabitatAtlasDataRelease'}
    def log(message):print(datetime.datetime.now(datetime.timezone.utc).isoformat(),str(message).replace(token,'[redacted]').replace(auth,'[redacted]'),flush=True)
    def state(stage,**kwargs):
        payload={'stage':stage,'updatedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),**kwargs};tmp=root/'release_status.tmp';tmp.write_text(json.dumps(payload,indent=2));tmp.replace(root/'release_status.json');log(stage)
    def run(*cmd,cwd=None):
        r=subprocess.run(list(map(str,cmd)),cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        if r.returncode:raise RuntimeError(r.stdout[-2000:].replace(token,'[redacted]').replace(auth,'[redacted]'))
        return r.stdout.strip()
    def published():
        try:
            r=requests.get('https://adawy2050.github.io/coastal-habitat/observed2026/manifest.json',params={'check':int(time.time())},timeout=30);r.raise_for_status();m=r.json()
            return m.get('allProductsComplete') and set(m.get('products',{}))=={'mur','oisst'}
        except Exception:return False
    state('Waiting for checked MUR outputs')
    deadline=time.monotonic()+24*3600
    while time.monotonic()<deadline:
        try:
            if published():state('Published',url='https://adawy2050.github.io/coastal-habitat/');return
            progress=json.loads((root/'status.json').read_text())
            if progress.get('status')!='complete':time.sleep(60);continue
            assert py.is_file(),'Release environment is missing'
            state('Confirming cross-year events');run(py,root/'boundary.py','--root',root,cwd=root)
            manifest=json.loads((root/'public/manifest.json').read_text());assert manifest['independentQCComplete'] and manifest['allProductsComplete']
            assert set(manifest['products'])=={'mur','oisst'}
            state('Preparing publication')
            checkout=root/'github-release'
            if not (checkout/'.git').exists():run('git','clone','--depth','1','--single-branch','--branch','main',REPO,checkout)
            assert run('git','remote','get-url','origin',cwd=checkout)==REPO
            run('git','fetch','origin','main',cwd=checkout);run('git','merge','--ff-only','origin/main',cwd=checkout)
            assert not run('git','diff','--cached','--name-only',cwd=checkout)
            target=checkout/'dist/observed2026'
            for name,entry in manifest['files'].items():
                source=root/'public'/name;destination=(target/name).resolve();assert target.resolve() in destination.parents
                assert source.stat().st_size==entry['bytes'] and hashlib.sha256(source.read_bytes()).hexdigest()==entry['sha256']
                destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,destination)
            shutil.copy2(root/'public/manifest.json',target/'manifest.json')
            # The independent checker re-extracts the same published curves.
            archive=json.loads((checkout/'dist/forecasts/iri_issue_archive.json').read_text());cache=checkout/'_cache/climate_forecasts';cache.mkdir(parents=True,exist_ok=True)
            for record in archive:
                file=cache/f"IRI_{record['issueMonth'].replace('-','')}_figure.svg"
                if not file.exists():
                    response=requests.get(record['source'],timeout=90);response.raise_for_status();file.write_bytes(response.content);time.sleep(.2)
            state('Checking data and cell models')
            for script in ['observed2026_fetch.py --verify-only','observed2026_summaries.py','forecast_index_models.py','verify_forecast_indices.py','build_assets.py','verify_assets.py','verify.py','verify_detail.py']:
                log(run(py,'scripts/'+script.split()[0],*script.split()[1:],cwd=checkout)[-500:])
            assert sum(p.stat().st_size for p in (checkout/'dist').rglob('*') if p.is_file())<1024**3
            changed=run('git','diff','--name-only',cwd=checkout).splitlines()
            assert all(p.startswith(('dist/observed2026/','dist/forecasts/')) or p=='dist/asset-manifest.json' for p in changed),changed
            run('git','add','dist/observed2026','dist/forecasts','dist/asset-manifest.json',cwd=checkout)
            if run('git','diff','--cached','--name-only',cwd=checkout):
                run('git','-c','user.name=Atlas data update','-c','user.email=adawy2050@users.noreply.github.com','commit','-m','Complete checked MUR observations through 20 October 2026 and refresh cell outlooks',cwd=checkout)
            sha=run('git','rev-parse','HEAD',cwd=checkout);run('git','push','origin','main',cwd=checkout)
            state('Deploying',commit=sha)
            for _ in range(90):
                r=requests.get(API+'/actions/workflows/pages.yml/runs',headers=headers,params={'per_page':5},timeout=40);r.raise_for_status();runs=[j for j in r.json()['workflow_runs'] if j['head_sha']==sha]
                if runs and runs[0]['status']=='completed':
                    if runs[0]['conclusion']=='success':state('Published',commit=sha,workflow=runs[0]['html_url'],url='https://adawy2050.github.io/coastal-habitat/');return
                    raise RuntimeError('GitHub deployment failed: '+runs[0]['html_url'])
                time.sleep(20)
            raise TimeoutError('GitHub deployment has not completed')
        except Exception as error:
            state('Publication retry',error=str(error).replace(token,'[redacted]').replace(auth,'[redacted]')[:1600]);time.sleep(300)
    state('Publication needs review',reason='The 24-hour watch ended before successful publication')

if __name__=='__main__':main()
