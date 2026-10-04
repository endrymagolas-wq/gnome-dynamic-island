import sys,tempfile,json,os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'assistant'))
from disk_history import DiskWatch,History,GiB
from monitor import Monitor
from collections import deque

def usage(free,total=100):return SimpleNamespace(total=total*GiB,free=free*GiB,used=(total-free)*GiB)
with patch('disk_history.Path.stat',return_value=SimpleNamespace(st_dev=1)),patch('disk_history.shutil.disk_usage') as space:
 w=DiskWatch();space.return_value=usage(4)
 events,recovered=w.update(now=0);assert len(events)==1 and len(w.snapshot)==1 and not recovered
 assert w.update(now=5)==([],False),'sample limit'
 assert w.update(now=30)==([],False),'repeat warning'
 space.return_value=usage(6);assert w.update(now=60)==([],False),'hysteresis chatter'
 space.return_value=usage(8);assert w.update(now=90)==([],True),'recovery'
 space.return_value=usage(4);assert len(w.update(now=120)[0])==1,'episode rearmed'
 space.side_effect=OSError();assert w.update(now=150)==([],False),'missing read is not recovery'
for free,total,expected in [(4.9,20,True),(5,20,False),(15,400,True),(20,500,False),(100,10000,False)]:
 with patch('disk_history.Path.stat',return_value=SimpleNamespace(st_dev=1)),patch('disk_history.shutil.disk_usage',return_value=usage(free,total)):
  assert bool(DiskWatch().update(now=0)[0])==expected,(free,total)
with patch('disk_history.Path.stat',side_effect=[SimpleNamespace(st_dev=1),SimpleNamespace(st_dev=2)]),patch('disk_history.shutil.disk_usage',side_effect=[usage(4),usage(3)]):
 assert len(DiskWatch().update(now=0)[0])==2,'distinct filesystems'
with tempfile.TemporaryDirectory() as td:
 p=Path(td)/'history.json';h=History(p)
 item={'kind':'cpu','title':'x'*100,'message':'m'*150,'advice':'a'*150}
 key=h.record(item);h.stage(key,'shown');h.recover('cpu');h.recover('cpu')
 assert h.entries[0]['stage']=='recovered'
 for i in range(75):h.record({**item,'title':str(i)})
 assert len(h.entries)==60 and len(h.recent())==5 and h.recent()[0]['title']=='74'
 assert p.stat().st_mode&0o777==0o600 and p.stat().st_size<65536
 assert len(History(p).entries)==60,'persisted reload'
 p.write_text('[{"kind":"cpu","stage":"shown","at":NaN}]');assert History(p).entries==[],'nonfinite input'
 p.write_text('invalid');assert History(p).entries==[],'corrupt input'
 h=History(Path(td)/'missing'/'history.json');h.record(item);assert not h.storage_ok,'write failure'
 h=History(Path(td)/'integration.json');m=Monitor.__new__(Monitor);m.history=h;m.queue=deque(maxlen=4);m.last_shown=0;m.shown_times=deque();m.kind_shown={};m.last_delivery=None
 key=h.record(item);m.queue.append({**item,'expires':5000,'history_id':key})
 with patch('monitor.time.time',return_value=1000),patch('monitor.shell_call',return_value=True):m.deliver({})
 assert h.entries[0]['stage']=='shown'
 m.queue.append({**item,'expires':999,'history_id':key})
 with patch('monitor.time.time',return_value=1000):m.deliver({})
 assert h.entries[0]['stage']=='expired'
print('PASS disk: thresholds, cooldown, dedup, two filesystems, hysteresis, unavailable reads; history: bounded/reload/private/corrupt/failure/delivery')
