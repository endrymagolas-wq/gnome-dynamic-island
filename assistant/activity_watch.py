"""Bounded lifecycle and user-service observers. No mutating system calls."""
import subprocess,time
TASK_NAMES={'make','ninja','cargo','cmake','gcc','g++','clang','clang++','rustc','javac','ffmpeg','avconv','7z','7za','zip','xz','zstd','tar','gzip'}
WATCHED={'ytmusic-airplay.service':'AirPlay аудіо','airplay-screen.service':'AirPlay екрана','open-webui.service':'Локальний AI-сервер'}

class TaskWatch:
    def __init__(self):self.tasks={};self.finished_count=0
    def update(self,processes,now=None):
        now=time.monotonic() if now is None else now
        identities={(p['pid'],p['start']):p for p in processes.values()}
        def descendants(pid):
            family={pid}
            for _ in range(32):
                found={p['pid'] for p in processes.values() if p['ppid'] in family}
                new=family|found
                if new==family:break
                family=new
            return {(p['pid'],p['start']) for p in processes.values() if p['pid'] in family}
        finished=[]
        for key,t in list(self.tasks.items()):
            t['members'].intersection_update(identities.keys())
            if key in identities:t['members'].update(descendants(key[0]))
            else:
                for member in list(t['members']):t['members'].update(descendants(member[0]))
            if t['members']:
                t['last_seen']=now;t['missing_since']=None;continue
            if t['missing_since'] is None:t['missing_since']=now
            if now-t['missing_since']>=10:
                duration=t['last_seen']-t['since']
                if duration>=30:
                    finished.append({'name':t['name'],'observed_seconds':round(duration),'exit_status_known':False})
                    self.finished_count+=1
                del self.tasks[key]
        for p in processes.values():
            key=(p['pid'],p['start'])
            if p['name'] not in TASK_NAMES or key in self.tasks or len(self.tasks)>=32:continue
            ancestor=processes.get(p['ppid']);seen=set();nested=False
            for _ in range(32):
                if not ancestor or ancestor['pid'] in seen:break
                seen.add(ancestor['pid'])
                if ancestor['name'] in TASK_NAMES:nested=True;break
                ancestor=processes.get(ancestor['ppid'])
            if nested or any(key in t['members'] for t in self.tasks.values()):continue
            self.tasks[key]={'name':p['name'],'since':now,'last_seen':now,'missing_since':None,'members':descendants(p['pid'])}
        return finished
    def status(self):return {'tracked':len(self.tasks),'completed_observations':self.finished_count,'minimum_observed_seconds':30,'exit_status_available':False}


def read_units():
    properties='Id,LoadState,UnitFileState,ActiveState,SubState,Result,NRestarts,ExecMainStatus'
    try:
        r=subprocess.run(['systemctl','--user','show',*WATCHED,'--property='+properties],capture_output=True,text=True,timeout=3)
    except (OSError,subprocess.TimeoutExpired):return None
    units={}
    for block in r.stdout.strip().split('\n\n'):
        row=dict(line.split('=',1) for line in block.splitlines() if '=' in line)
        if row.get('Id') in WATCHED:units[row['Id']]=row
    return units or None

class ServiceWatch:
    def __init__(self):self.previous={};self.snapshot={};self.last_sample=0;self.episodes={}
    def update(self,units=None,now=None,force=False):
        now=time.monotonic() if now is None else now
        if units is None:
            if not force and now-self.last_sample<10:return []
            units=read_units()
            if units is None:return []
        self.last_sample=now;events=[]
        for unit,row in units.items():
            if unit not in WATCHED or row.get('LoadState')!='loaded':continue
            active=row.get('ActiveState','unknown')
            try:restarts=int(row.get('NRestarts','0') or 0)
            except ValueError:continue
            old=self.previous.get(unit);episode=self.episodes.setdefault(unit,{'armed':False,'reported':False,'good_since':None})
            if active=='active' or row.get('UnitFileState','').startswith('enabled'):episode['armed']=True
            jumped=old is not None and restarts>old['restarts']
            failed=active=='failed' or (active=='inactive' and row.get('Result','success') not in ['success',''])
            restarting=row.get('SubState')=='auto-restart' or jumped
            if active=='active' and not jumped:
                if episode['good_since'] is None:episode['good_since']=now
                if now-episode['good_since']>=60:episode['reported']=False
            else:episode['good_since']=None
            if episode['armed'] and (failed or restarting) and not episode['reported']:
                episode['reported']=True
                events.append({'unit':unit,'name':WATCHED[unit],'state':active,'restarted':restarting,'exit_status':row.get('ExecMainStatus','unknown')})
            self.previous[unit]={'restarts':restarts,'state':active}
            self.snapshot[unit]={'name':WATCHED[unit],'state':active,'substate':row.get('SubState'),'result':row.get('Result'),'restarts':restarts,'armed':episode['armed']}
        return events
    def status(self):return {'units':self.snapshot,'automatic_restart':False}
