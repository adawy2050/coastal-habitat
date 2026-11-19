"""Keep the isolated update resumable; retry network failures, stop on failed QC."""
from pathlib import Path
import argparse,json,subprocess,sys,time
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();root=a.root.resolve()
for attempt in range(120):
 with (root/'worker.log').open('ab') as log:r=subprocess.run([sys.executable,'-u',str(root/'worker.py'),'--root',str(root)],stdout=log,stderr=subprocess.STDOUT)
 if r.returncode==0:break
 try:status=json.loads((root/'status.json').read_text())
 except Exception:break
 if not status.get('retryable'):break
 time.sleep(120)
