"""Wait for the two read-only exports, then transfer the compact atlas package."""
from pathlib import Path
import hashlib,shlex,tarfile,time
import paramiko
ROOT=Path(__file__).resolve().parents[1];REMOTE='/minamitori/data2/eladawy/ATLAS_EASTASIA_EXPORT_20261018'
def main():
    client=paramiko.SSHClient();client.load_system_host_keys();client.connect('172.24.30.56',username='eladawy',key_filename=str(Path.home()/'.ssh/id_rsa'),timeout=25)
    previous=None
    for attempt in range(240):
        f=client.open_sftp()
        logs=[f.open(REMOTE+'/'+name).read().decode() for name in ['worker.log','sst.log']];f.close()
        if any('Traceback' in log for log in logs):raise RuntimeError('\n'.join(logs)[-3000:])
        status=[log.splitlines()[-1] if log.splitlines() else 'Mapping marine cells' for log in logs]
        if status!=previous:print(' | '.join(status),flush=True);previous=status
        if logs[0].rstrip().endswith('COMPLETE') and 'DAILY COMPLETE' in logs[1]:break
        time.sleep(30)
    else:raise TimeoutError('Export still running; source files untouched')
    code=f"""from pathlib import Path
import tarfile,hashlib
root=Path({REMOTE!r});out=root/'export';paths=[p for p in out.iterdir() if p.suffix=='.f32' or p.name in ['mur_monthly.npy','oisst_monthly.npy','mur_attachment.npz','oisst_attachment.npz','oisst_daily.npz','sites.csv','validation.json']]
with tarfile.open(root/'atlas_export.tar.gz','w:gz') as tar:
 for p in paths:tar.add(p,arcname=p.name)
print(hashlib.sha256((root/'atlas_export.tar.gz').read_bytes()).hexdigest())
"""
    _,stdout,stderr=client.exec_command('python -c '+shlex.quote(code),timeout=240);digest=stdout.read().decode().strip();error=stderr.read().decode();assert len(digest)==64,error
    target=ROOT/'_cache/eastasia_export';target.mkdir(parents=True,exist_ok=True);archive=ROOT/'_cache/eastasia_export.tar.gz';f=client.open_sftp();f.get(REMOTE+'/atlas_export.tar.gz',str(archive));f.close();client.close();assert hashlib.sha256(archive.read_bytes()).hexdigest()==digest
    with tarfile.open(archive) as tar:tar.extractall(target,filter='data')
    print('EXPORT DOWNLOADED',archive.stat().st_size,'bytes',digest,flush=True)
if __name__=='__main__':main()
