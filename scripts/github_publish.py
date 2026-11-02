"""Publish the prepared atlas. Read a GitHub token from stdin; never save it.

Only the dedicated named repository is touched. A pre-existing nonempty repository
is accepted only when its README identifies this same atlas.
"""
from __future__ import annotations
import argparse
import base64
import getpass
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--owner', default='adawy2050')
    parser.add_argument('--repo', default='redsea-habitat-mhw-atlas')
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--staged-only', action='store_true', help='Publish the current staged commit without adding in-progress assets')
    parser.add_argument('--git-auth', action='store_true', help='Use the existing GitHub sign-in through the normal Git credential helper; no credential is printed or saved')
    args = parser.parse_args()
    if args.git_auth:
        credential_env = os.environ.copy()
        credential_env.update({'GIT_TERMINAL_PROMPT':'0','GCM_INTERACTIVE':'Never'})
        credentials = subprocess.run(['git','-c','credential.interactive=never','credential','fill'],
            input=f'protocol=https\nhost=github.com\nusername={args.owner}\n\n',
            cwd=ROOT, env=credential_env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        fields = dict(line.split('=',1) for line in credentials.stdout.splitlines() if '=' in line)
        token = fields.get('password','') if credentials.returncode == 0 else ''
        print('Using the existing GitHub sign-in through Git credential helper.', flush=True)
    else:
        print('Ready for GitHub token on stdin (not echoed or stored).', flush=True)
        token = getpass.getpass('GitHub token (hidden): ').strip()
    if not token:
        raise SystemExit('No credential supplied.')
    def api(method, path, body=None, optional=False):
        payload = json.dumps(body).encode() if body is not None else None
        request = Request('https://api.github.com'+path, data=payload, method=method,
            headers={'Authorization': 'Bearer '+token, 'Accept':'application/vnd.github+json',
                     'X-GitHub-Api-Version':'2022-11-28', 'Content-Type':'application/json', 'User-Agent':'Red-Sea-Habitat-Atlas'})
        try:
            with urlopen(request, timeout=60) as response:
                raw=response.read()
                return json.loads(raw) if raw else {}
        except HTTPError as error:
            if optional and error.code == 404:
                return None
            detail = json.loads(error.read().decode()).get('message','Request failed')
            raise RuntimeError(f'GitHub {method} {path}: HTTP {error.code}: {detail.replace(token,"[redacted]")}') from None
    user = api('GET','/user')
    print('Authenticated account:',user['login'],flush=True)
    if user['login'].lower()!=args.owner.lower():
        raise SystemExit('The credential belongs to a different account; publication stopped.')
    repo_path=f'/repos/{args.owner}/{args.repo}'
    repo=api('GET',repo_path,optional=True)
    if args.check_only:
        print('Repository exists:',repo is not None,flush=True)
        return
    if repo is None:
        repo=api('POST','/user/repos',{'name':args.repo,'description':'Interactive habitat-pixel marine heatwave atlas for the Red Sea and Gulf of Aden, with climate indices and annual histories.', 'private':False,'auto_init':False,'homepage':f'https://{args.owner}.github.io/{args.repo}/'})
        print('Created public repository:',repo['html_url'],flush=True)
    elif repo.get('size',0)>0:
        contents=api('GET',repo_path+'/contents/README.md',optional=True)
        if not contents or not base64.b64decode(contents.get('content','')).decode(errors='replace').startswith(('# Red Sea Habitat Heatwave Atlas','# Red Sea & Arabian Gulf Habitat Heatwave Atlas','# Coastal Habitat Heatwave Atlas','# Coastal habitat observatory')):
            raise SystemExit('An unrelated nonempty repository has this name; it was left unchanged.')
    api('PATCH',repo_path,{'description':'Marine heatwave maps for coastal habitats across the Red Sea, Arabian Gulf, East Asia and western Pacific.','homepage':f'https://{args.owner}.github.io/{args.repo}/'})
    # Credentials live only in child-process environment, never command arguments/config files.
    env=os.environ.copy()
    auth=base64.b64encode(('x-access-token:'+token).encode()).decode()
    env.update({'GIT_CONFIG_COUNT':'1','GIT_CONFIG_KEY_0':'http.https://github.com/.extraheader',
                'GIT_CONFIG_VALUE_0':'AUTHORIZATION: basic '+auth,'GIT_TERMINAL_PROMPT':'0'})
    def git(*arguments,check=True):
        r=subprocess.run(['git',*arguments],cwd=ROOT,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        output=r.stdout.replace(token,'[redacted]').replace(auth,'[redacted]')
        if output.strip():
            print(output.strip(),flush=True)
        if check and r.returncode:
            raise RuntimeError('Git command failed; credential was not saved.')
        return r
    if not (ROOT/'.git').exists():
        git('init','-b','main')
        git('config','user.name',user.get('name') or user['login'])
        git('config','user.email',f'{user["id"]}+{user["login"]}@users.noreply.github.com')
        git('remote','add','origin',repo['clone_url'])
    remote=git('remote','get-url','origin').stdout.strip()
    if remote!=repo['clone_url']:
        raise SystemExit('Existing local remote differs from target repository; publication stopped.')
    if not args.staged_only:git('add','dist','scripts','.github','.gitignore','.gitattributes','README.md','DATA_METHODS.md','preview.ps1')
    changes=git('diff','--cached','--quiet',check=False)
    if changes.returncode:
        git('commit','-m','Build interactive habitat-pixel heatwave atlas with validated study data')
    git('push','-u','origin','main')
    expected_sha=git('rev-parse','HEAD').stdout.strip()
    print('SOURCE_PUSHED',repo['html_url'],flush=True)
    pages=api('GET',repo_path+'/pages',optional=True)
    if pages is None:
        pages=api('POST',repo_path+'/pages',{'build_type':'workflow'})
        print('GitHub Pages enabled with Actions.',flush=True)
    elif pages.get('build_type')!='workflow':
        pages=api('PUT',repo_path+'/pages',{'build_type':'workflow'})
    last=None
    for k in range(30):
        runs=[run for run in api('GET',repo_path+'/actions/workflows/pages.yml/runs?per_page=5').get('workflow_runs',[]) if run['head_sha']==expected_sha]
        if runs:
            run=runs[0]
            status=(run['status'],run.get('conclusion'))
            if status!=last:
                print('Deployment:',status,run['html_url'],flush=True)
                last=status
            if status[0]=='completed':
                if status[1]=='success':
                    pages=api('GET',repo_path+'/pages')
                    result={'repository':repo['html_url'],'url':pages['html_url'],'workflow':run['html_url'],'status':'deployed'}
                    (ROOT/'qa').mkdir(exist_ok=True)
                    (ROOT/'qa/deployment.json').write_text(json.dumps(result,indent=2))
                    print('DEPLOYED',result['url'],flush=True)
                    return
                raise RuntimeError('The GitHub Pages workflow did not succeed. See the reported workflow URL.')
        time.sleep(15)
    print('Deployment still pending. Source is safely pushed; inspect repository Actions.',flush=True)


if __name__=='__main__':
    try:
        main()
    except Exception as error:
        print(str(error),flush=True)
        raise SystemExit(1)
