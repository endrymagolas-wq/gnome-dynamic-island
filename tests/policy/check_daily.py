import sys,tempfile,json
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'assistant'))
import preferences
from network_watch import NetworkWatch
from monitor import Monitor
from classifier_pool import ClassifierPool
from collections import deque
w=NetworkWatch()
assert w.update(now=0,value='online') is None
assert w.update(now=5,value='offline') is None
assert w.update(now=10,value='online') is None,'short disconnect not debounced'
assert w.update(now=15,value='offline') is None
assert w.update(now=20,value='offline') is None
assert w.update(now=25,value='offline')=={'state':'offline'}
assert w.update(now=30,value='offline') is None
assert w.update(now=35,value='online') is None
assert w.update(now=45,value='online')=={'state':'online'}
with patch('network_watch.connectivity',return_value=None):assert w.update(now=50,force=True) is None and w.snapshot['state']=='unknown'
with tempfile.TemporaryDirectory() as td:
 p=Path(td)/'prefs.json';assert preferences.read(p)['economy']
 preferences.write({'enabled':False,'economy':False,'muted_kinds':['cpu','unsupported']},p)
 assert preferences.read(p)=={'enabled':False,'economy':False,'muted_kinds':['cpu']}
 assert p.stat().st_mode&0o777==0o600
 p.write_text('invalid');assert preferences.read(p)['enabled']
 p.write_text('{"muted_kinds":null}');assert preferences.read(p)['muted_kinds']==[]
m=Monitor(history_path=Path(tempfile.mkdtemp())/'history.json')
assert m.classifier.proc is None and 'torch' not in sys.modules,'resident model in collector'
m.preferences['muted_kinds']=['cpu'];assert m.decide('cpu',{})['action']=='muted' and not m.pending
m.preferences['muted_kinds']=[];m.decide('connection',{});m.process_model({'focusActive':True});assert m.classifier.proc is None and m.pending,'cold load during focus'
assert len(m.history.entries)==1,'fast event policy missing'
m.metrics={'ram':95};m.process_model({});assert len(m.history.entries)==1,'fast event notification repeated'
assert m.classifier.proc is None and m.last_decision['classifier_source']=='system_pressure_policy'
m.preferences['muted_kinds']=['connection'];m.process_model({});assert not m.queue,'queued muted event displayed'
m.classifier.close()
pool=ClassifierPool();pool.started=0;pool.last_used=0;pool.proc=SimpleNamespace()
with patch.object(pool,'close') as close,patch('classifier_pool.time.monotonic',return_value=61):pool.maintain();close.assert_called_once_with('idle')
with patch.object(pool,'close') as close:pool.maintain(economy=False,pressure=True);close.assert_called_once_with('system_pressure')
print('PASS network debounce/recovery/unknown; private preferences; no torch in parent; muted events; quiet-context cold load; pressure fallback; idle and pressure lifecycle')
