import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'assistant'))
from collections import deque
from unittest.mock import patch
from monitor import Monitor

def bare():
 m=Monitor.__new__(Monitor);m.queue=deque(maxlen=4);m.last_shown=0;m.last_delivery=None;m.shown_times=deque();m.kind_shown={};return m

def event(kind):return {'kind':kind,'expires':5000}
with patch('monitor.shell_call',return_value=True) as bridge:
 m=bare()
 for at,kind in [(1000,'connection'),(1010,'download'),(1020,'cpu'),(1030,'ram')]:
  m.queue.append(event(kind))
  with patch('monitor.time.time',return_value=at):m.deliver({})
 assert bridge.call_count==3 and len(m.queue)==1,'Burst cap failed'
 m=bare();bridge.reset_mock()
 for at in [2000,2010,2070]:
  m.queue.append(event('connection'))
  with patch('monitor.time.time',return_value=at):m.deliver({})
 assert bridge.call_count==2,'Duplicate debounce failed'
 m=bare();bridge.reset_mock();m.queue.append(event('download'))
 with patch('monitor.time.time',return_value=1000):
  m.deliver({'focusActive':True});m.deliver({'fullscreen':True});m.deliver({'menuOpen':True})
 assert bridge.call_count==0 and len(m.queue)==1,'Suppressed context consumed or displayed event'
 m.queue[0]['expires']=999
 with patch('monitor.time.time',return_value=1000):m.deliver({})
 assert not m.queue and bridge.call_count==0,'Stale event displayed'
m=bare();m.seen=0;m.previous_files={};m.changing={};m.previous_cpu=(0,0);m.high_since={};m.cooldowns={};m.resource_notified=set();seen=[];m.decide=lambda k,s:seen.append(k)
with patch('monitor.files',return_value={}),patch('monitor.ram_percent',return_value=0):
 m.downloads=Path('/unused')
 for at,cpu in [(500,(100,0)),(561,(200,0)),(1200,(300,0)),(1210,(400,100)),(1600,(500,100)),(1661,(600,100))]:
  if at==1210:m.queue.append(event('cpu'))
  with patch('monitor.time.monotonic',return_value=at),patch('monitor.cpu_sample',return_value=cpu):m.collect({})
  if at==1210:assert not m.queue,'Recovered resource notification remained queued'
assert seen==['cpu','cpu'],seen
print('PASS: max3/5min; same-kind60s; focus/fullscreen/menu; expired events; one resource notification per overload episode')
