"""Launch/resume the isolated server worker and pull a public progress snapshot."""
from pathlib import Path
import argparse,json,shlex,time
import numpy as np
import paramiko
ROOT=Path(__file__).resolve().parents[1]
REMOTE='/minamitori/data2/eladawy/ATLAS_UPDATE_20261022'
def connection():
 c=paramiko.SSHClient();c.load_system_host_keys();c.connect('172.24.30.56',username='eladawy',key_filename=str(Path.home()/'.ssh/id_rsa'),timeout=25);return c
def upload_qc(f):
 cache=ROOT/'_cache/observed2026';cache.mkdir(parents=True,exist_ok=True);meta=json.loads((ROOT/'dist/data/metadata.json').read_text());values=[]
 for basin in ['redsea','gulf']:
  p=ROOT/'dist/detail/daily'/basin;j=json.loads((p/'index.json').read_text());dates=np.array(j['dates']);keep=dates>='2024-01-01';start,end=meta['products']['oisst']['basinCellRanges'][basin];assert j['cells']==meta['products']['oisst']['cells'][start:end];values.append(np.column_stack([np.fromfile(p/f'{i}.i16',dtype='<i2')[keep]*.01 for i in range(len(j['cells']))]))
 np.savez_compressed(cache/'oisst_old_raw2024_2025.npz',values=np.column_stack(values),dates=dates[keep]);np.save(cache/'oisst_old_2025_days.npy',np.fromfile(ROOT/'dist/data/oisst_mhw_days.f32',dtype='<f4').reshape(44,-1)[-1,:483])
 for name in ['oisst_old_raw2024_2025.npz','oisst_old_2025_days.npy']:f.put(str(cache/name),REMOTE+'/'+name)

def main():
 a=argparse.ArgumentParser();a.add_argument('--launch',action='store_true');a.add_argument('--watch',action='store_true');args=a.parse_args();out=ROOT/'dist/observed2026';out.mkdir(parents=True,exist_ok=True)
 while True:
  c=connection()
  try:
   if args.launch:
    _,o,e=c.exec_command('mkdir -p '+shlex.quote(REMOTE));o.channel.recv_exit_status();f=c.open_sftp();f.put(str(ROOT/'scripts/observed2026_remote.py'),REMOTE+'/worker.py');f.put(str(ROOT/'scripts/observed2026_supervise.py'),REMOTE+'/supervise.py');f.put(str(ROOT/'dist/data/metadata.json'),REMOTE+'/metadata.json');upload_qc(f);f.close()
    cmd=f'cd {shlex.quote(REMOTE)} && if test -f worker.pid && kill -0 $(cat worker.pid) 2>/dev/null; then cat worker.pid; else nohup python -u supervise.py --root {shlex.quote(REMOTE)} >> supervisor.log 2>&1 < /dev/null & echo $! > worker.pid; cat worker.pid; fi'
    _,o,e=c.exec_command(cmd);print('Remote worker PID',o.read().decode().strip(),e.read().decode().strip(),flush=True);args.launch=False;time.sleep(2)
   f=c.open_sftp();snapshot=json.loads(f.open(REMOTE+'/status.json').read());snapshot['snapshotAt']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime());snapshot['monitorMode']='server worker with periodically published snapshots';p=out/'status.json';tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(snapshot,ensure_ascii=False,separators=(',',':')),encoding='utf-8');tmp.replace(p);print(json.dumps(snapshot,ensure_ascii=False),flush=True)
   if snapshot.get('status')=='complete':
    # Individual content downloads are explicit via --fetch in a later export, so status polling stays small.
    print('SERVER ANALYSIS COMPLETE',flush=True)
   f.close()
  finally:c.close()
  if not args.watch or snapshot.get('status') in ['complete','failed']:break
  time.sleep(30)
if __name__=='__main__':main()
