import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'assistant'))
from activity_watch import TaskWatch,ServiceWatch

def p(pid,name,ppid=1,start=500):return {'pid':pid,'name':name,'ppid':ppid,'start':start}
t=TaskWatch();root=p(10,'make');child=p(11,'gcc',10)
assert not t.update({10:root,11:child},0);assert len(t.tasks)==1
assert not t.update({10:root,11:child},40)
assert not t.update({11:child},50),'Parent disappearance must not complete running child'
assert not t.update({},60),'Needs two missing samples'
r=t.update({},70);assert len(r)==1 and r[0]['observed_seconds']==50 and not r[0]['exit_status_known'],r
# Short tasks are silent, and PID reuse is separate identity.
t=TaskWatch();assert not t.update({10:p(10,'ffmpeg')},0)
assert not t.update({10:p(10,'ffmpeg')},10)
assert not t.update({},20);assert not t.update({},30)
t=TaskWatch();t.update({10:p(10,'ffmpeg')},0);t.update({10:p(10,'ffmpeg')},40)
t.update({10:p(10,'ffmpeg',start=999)},50);r=t.update({10:p(10,'ffmpeg',start=999)},60)
assert len(r)==1 and len(t.tasks)==1
# Brief read failure must not complete a still-running task.
t=TaskWatch();t.update({10:root},0);t.update({10:root},40);t.update({},50)
assert not t.update({10:root},60)
unit='ytmusic-airplay.service'
def row(active,sub='running',restarts=0,result='success',enabled=True):return {unit:{'LoadState':'loaded','UnitFileState':'enabled' if enabled else 'disabled','ActiveState':active,'SubState':sub,'NRestarts':str(restarts),'Result':result,'ExecMainStatus':'0'}}
s=ServiceWatch();assert not s.update(row('inactive',enabled=False),0)
assert not s.update(row('active'),10)
assert not s.update(row('inactive',sub='dead'),20),'Intentional clean stop is silent'
r=s.update(row('failed',sub='failed',result='exit-code'),30);assert len(r)==1
assert not s.update(row('failed',sub='failed',result='exit-code'),40),'Failure repeats suppressed'
assert not s.update(row('active'),50);assert not s.update(row('active'),111)
r=s.update(row('active',restarts=1),120);assert len(r)==1 and r[0]['restarted']
assert not s.update(row('active',restarts=2),130),'Restart loop is one episode'
s=ServiceWatch();assert not s.update(row('active',restarts=9),0),'Historical restart count is baselined'
print('PASS: long/short/nested tasks, child survival, two-sample disappearance, PID reuse, read hiccup; inactive/clean-stop silence, failure episode, recovery and restart loop')
