import sys,time,tempfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'assistant'))
from monitor import Monitor
class Pool:
 ready=True;job=None;responses=[];closed=None
 def poll(self):
  result=self.responses;self.responses=[]
  if result:self.job=None
  return result
 def maintain(self,*args):pass
 def submit(self,key,state,schema):self.job=key;return True
 def close(self,reason='disabled'):self.closed=reason;self.job=None
m=Monitor(history_path=Path(tempfile.mkdtemp())/'journal.json');m.classifier=Pool()
m.decide('download',{});m.process_model({});key=m.inflight['id']
m.preferences['muted_kinds']=['download'];m.process_model({});assert m.inflight is None and m.classifier.closed=='muted' and not m.queue
m.preferences['muted_kinds']=[];m.decide('disk',{}, {'name':'Система','free_gib':3});m.process_model({});job=m.inflight
job['expires']=time.time()-1;m.classifier.responses=[{'id':job['id'],'answer':{'choice':'resource','answer_confidence':.9,'probabilities':{}}}];m.process_model({});assert not m.queue,'expired classifier result shown'
m.classifier.ready=False;m.decide('connection',{});assert len(m.queue)==1 and len(m.history.entries)==1
m.process_model({});job=m.inflight;m.classifier.responses=[{'id':job['id'],'answer':{'choice':'connection','answer_confidence':.9,'probabilities':{}}}];m.process_model({});assert len(m.queue)==1 and len(m.history.entries)==1,'cold audit duplicated notice'
m.queue.clear();m.last_shown=0;m.shown_times.clear();m.kind_shown.clear()
with patch('monitor.shell_call',return_value=True) as bridge:
 for at,state in [(1000,'offline'),(1020,'online')]:
  m.queue.append({'kind':'network','source_detail':{'state':state},'expires':5000})
  with patch('monitor.time.time',return_value=at):m.deliver({})
 assert bridge.call_count==2,'stable network recovery suppressed'
print('PASS inflight mute cleanup, expired model results, no duplicate cold audit, network loss and recovery retain global noise cap')
