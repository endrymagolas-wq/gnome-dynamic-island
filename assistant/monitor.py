#!/usr/bin/env python3
"""Local event collector and actual Laya classifier. No cloud/API or desktop commands."""
import os
os.environ.setdefault('USE_TF','0');os.environ.setdefault('HF_HUB_OFFLINE','1')
import ast,json,logging,signal,subprocess,time,uuid
from pathlib import Path
from collections import deque
import preferences
from classifier_pool import ClassifierPool
from music_scene import MusicScene
from network_watch import NetworkWatch
from process_observer import ProcessObserver,recommendation
from activity_watch import TaskWatch,ServiceWatch
from disk_history import DiskWatch,History
BASE=Path(__file__).resolve().parent
MODEL=Path(os.environ.get('ISLAND_LAYA_MODEL', str(Path(__file__).resolve().parent/'model'/'multilingual')))
QUESTIONS={'category':{'type':'choice','instructions':'Classify this desktop system event. Select the category matching the event description.','criteria':{'connection':'A phone connected through AirPlay and is ready to play music.','completed':'A file download completed, or a long-running build/export task finished running; success may be unknown.','resource':'Sustained very high CPU or RAM usage lasting at least a minute.','routine':'A brief CPU spike or routine update; no persistent issue.','service':'An important background service failed or restarted unexpectedly.'}}}
TASK_QUESTIONS={'category':{'type':'choice','instructions':'Identify the observed process lifecycle event. Success or failure of its work is not being judged.','criteria':{'completed':'A long-running task process has stopped running.','routine':'The process is still running, or this is only a brief metric change.'}}}
DISK_QUESTIONS={'category':{'type':'choice','instructions':'Identify the observed filesystem free-space condition.','criteria':{'resource':'A filesystem has critically low remaining disk space.','routine':'The filesystem has enough free disk space.'}}}
NETWORK_QUESTIONS={'category':{'type':'choice','instructions':'Identify whether network connectivity changed after a stable observation.','criteria':{'network':'The Internet connection was lost or restored.','routine':'There was no stable network connectivity change.'}}}
TEMPLATES={'network':('Стан мережі змінився','Перевір підключення','network-wireless-symbolic'),'disk':('Мало місця на диску','Перевір великі файли','drive-harddisk-symbolic'),'connection':('AirPlay під’єднано','Телефон готовий до музики','audio-headphones-symbolic'),'download':('Завантаження готове','Новий файл у папці завантажень','folder-download-symbolic'),'cpu':('Високе навантаження CPU','Понад 95% протягом хвилини','utilities-system-monitor-symbolic'),'task':('Задача завершила роботу','Довга задача більше не працює','media-playback-stop-symbolic'),'service':('Служба потребує уваги','Важлива служба мала збій','dialog-warning-symbolic'),'ram':('Мало вільної пам’яті','Використано понад 90% RAM','utilities-system-monitor-symbolic')}
EVENTS={'network':('Internet connectivity changed after a stable observation.','network'),'disk':('A filesystem has critically low remaining disk space.','resource'),'connection':('AirPlay phone connected; audio is ready.','connection'),'download':('File download finished successfully.','completed'),'cpu':('CPU usage has stayed above 95 percent for over 60 seconds.','resource'),'task':('A long-running build or export task finished running; the exit status is unknown.','completed'),'service':('An important background service failed or restarted unexpectedly.','service'),'ram':('RAM usage has stayed above 90 percent for over 60 seconds.','resource')}
LOG=logging.getLogger('laya-island')
logging.basicConfig(level=logging.INFO,format='%(message)s')

def shell_call(method,*args):
    try:
        r=subprocess.run(['gdbus','call','--session','--dest','org.gnome.Shell','--object-path','/org/avalon/AirplayIsland','--method','org.avalon.AirplayIsland.'+method,*args],capture_output=True,text=True,timeout=3)
        if r.returncode:return None
        output=r.stdout.strip()
        if output=='(true,)':return True
        if output=='(false,)':return False
        return ast.literal_eval(output)[0]
    except (OSError,ValueError,SyntaxError,subprocess.TimeoutExpired):return None

def delivery_key(item):
    return 'network:'+str((item.get('source_detail') or {}).get('state','change')) if item['kind']=='network' else item['kind']

def status_write(data):
    tmp=BASE/'status.tmp';tmp.write_text(json.dumps(data,ensure_ascii=False));tmp.chmod(0o600);tmp.replace(BASE/'status.json')

def download_dir():
    try:
        p=subprocess.run(['xdg-user-dir','DOWNLOAD'],capture_output=True,text=True,timeout=2)
        if p.returncode==0 and p.stdout.strip():return Path(p.stdout.strip())
    except (OSError,subprocess.TimeoutExpired):pass
    return Path.home()/'Downloads'

def files(directory):
    result={}
    try:
        with os.scandir(directory) as entries:
            for i,f in enumerate(entries):
                if i>=2000:break
                if f.name.startswith('.') or f.name.endswith(('.crdownload','.part','.tmp','.download')):continue
                try:
                    if f.is_file(follow_symlinks=False):
                        s=f.stat(follow_symlinks=False);result[f.name]=(s.st_size,s.st_mtime_ns)
                except OSError:pass
    except OSError:pass
    return result

def cpu_sample():
    vals=[int(x) for x in Path('/proc/stat').read_text().splitlines()[0].split()[1:9]]
    return sum(vals),vals[3]+vals[4]

def ram_percent():
    m={x.split(':')[0]:int(x.split()[1]) for x in Path('/proc/meminfo').read_text().splitlines()}
    return 100*(1-m['MemAvailable']/m['MemTotal'])

class Monitor:
    def __init__(self,history_path=None):
        self.classifier=ClassifierPool();self.music=MusicScene();self.pending=deque(maxlen=4);self.inflight=None;self.event_versions={}
        self.preferences=preferences.read();self.metrics={};self.model_retry_after=0;self.network_watch=NetworkWatch()
        self.queue=deque(maxlen=4);self.running=True;self.inferences=0;self.last_decision=None;self.last_delivery=None
        self.downloads=download_dir();self.previous_files=files(self.downloads);self.changing={}
        self.previous_cpu=cpu_sample();self.high_since={};self.cooldowns={};self.last_shown=0;self.seen=None
        self.resource_notified=set();self.shown_times=deque();self.kind_shown={}
        self.observer=ProcessObserver();self.processes=None;self.last_recommendation=None
        self.task_watch=TaskWatch();self.service_watch=ServiceWatch();self.task_generation=0
        self.disk_watch=DiskWatch();self.history=History(history_path or BASE/'history.json')
        for entry in list(self.history.entries):
            if entry['stage']=='queued':self.history.stage(entry['id'],'expired')
    def decide(self,kind,state,detail=None):
        if kind in self.preferences['muted_kinds']:return {'kind':kind,'action':'muted'}
        key=str(uuid.uuid4());self.event_versions[kind]=key
        self.pending=deque((j for j in self.pending if j['kind']!=kind),maxlen=4)
        job={'id':key,'kind':kind,'detail':detail,'expires':time.time()+300}
        if kind in ['connection','network'] and self.preferences['economy'] and not self.classifier.ready:
            self._finish(job,state,source='fast_event_policy');job['notified']=True
        self.pending.append(job)
        return {'kind':kind,'action':'pending'}
    def _finish(self,job,state,result=None,source='laya'):
        kind=job['kind'];detail=job['detail'];expected=EVENTS[kind][1]
        if job['id']!=self.event_versions.get(kind) or kind in self.preferences['muted_kinds'] or job['expires']<time.time():return
        context='fullscreen' if state.get('fullscreen') else 'focus' if state.get('focusActive') else 'normal'
        category=result.get('choice') if result else expected;confidence=result.get('answer_confidence',0) if result else 1
        action='ignore' if category!=expected or confidence<.65 else 'defer' if context!='normal' else 'show'
        decision={'at':time.time(),'kind':kind,'category':category,'probabilities':result.get('probabilities',{}) if result else {},'action':action,'context':context,'classifier_source':source,'inference_ms':round((time.monotonic()-job.get('started',time.monotonic()))*1000)}
        if result:self.inferences+=1
        self.last_decision=decision;LOG.info(json.dumps({'decision':decision},ensure_ascii=False))
        if action!='ignore' and not job.get('notified'):
            # Latest notification of each kind wins; bounded queue and expiration.
            for previous in self.queue:
                if previous['kind']==kind:self.history.stage(previous.get('history_id'),'superseded')
            self.queue=deque((x for x in self.queue if x['kind']!=kind),maxlen=4)
            title,message,icon=TEMPLATES[kind]
            advice=None
            if kind in ['cpu','ram']:
                advice=recommendation(kind,self.processes);self.last_recommendation=advice
                if advice:message=advice['message']
            if kind=='task' and detail:
                seconds=detail['observed_seconds'];duration=f'{seconds} с' if seconds<60 else f'{seconds//60} хв'
                message=f"{detail['name']} · {duration}"
                if detail.get('count',1)>1:
                    title='Задачі завершили роботу';message=f"{detail['name']} та ще {detail['count']-1}"
                advice={'advice':'Перевір результат у програмі'}
            if kind=='service' and detail:
                message=detail['name']+(' · перезапускалась' if detail['state']=='active' else ' · мала збій')
                advice={'advice':'Перевір стан і журнал служби'}
            if kind=='network' and detail:
                title='Інтернет відновився' if detail['state']=='online' else 'Інтернет недоступний'
                message='Підключення знову працює' if detail['state']=='online' else 'Мережа не підтверджує доступ до інтернету'
                advice={'advice':'NetworkManager · стабільна зміна'}
            if kind=='disk' and detail:
                message=f"{detail['name']} · вільно {detail['free_gib']:.1f} ГіБ"
                if detail.get('count',1)>1:message+=f" · ще {detail['count']-1} диск"
                advice={'advice':'Перевір великі файли перед очищенням'}
            item={'kind':kind,'title':title,'message':message,'icon':icon,'advice':advice['advice'] if advice else None,'expires':time.time()+300,'decision':decision,'source_detail':detail}
            item['history_id']=self.history.record(item)
            if len(self.queue)==self.queue.maxlen:self.history.stage(self.queue[0].get('history_id'),'superseded')
            self.queue.append(item)
        return decision
    def process_model(self,state):
        muted=set(self.preferences['muted_kinds'])
        if self.inflight and self.inflight['kind'] in muted:
            self.classifier.close('muted');self.inflight=None
        self.pending=deque((j for j in self.pending if j['kind'] not in muted and j['expires']>=time.time()),maxlen=4)
        for item in self.queue:
            if item['kind'] in muted:self.history.stage(item.get('history_id'),'quiet')
        self.queue=deque((item for item in self.queue if item['kind'] not in muted),maxlen=4)
        for response in self.classifier.poll():
            if self.music.accept(response):
                if response.get('answer'):self.inferences+=1
                continue
            if self.inflight and response.get('id') in [None,self.inflight['id']]:
                job=self.inflight;self.inflight=None
                if response.get('answer'):self._finish(job,state,response['answer'])
                else:self.model_retry_after=time.monotonic()+300;self._finish(job,state,source='model_unavailable_policy')
        pressure=self.metrics.get('cpu',0)>=95 or self.metrics.get('ram',0)>=90
        if pressure:
            self.classifier.close('system_pressure');self.music.cancel()
            if self.inflight:self._finish(self.inflight,state,source='system_pressure_policy');self.inflight=None
        self.classifier.maintain(self.preferences['economy'],pressure)
        if self.inflight or self.classifier.job is not None:return
        if not self.pending:
            if not pressure and time.monotonic()>=self.model_retry_after:self.music.submit(self.classifier)
            return
        # No cold model load just to queue a notice during a quiet context.
        if state.get('fullscreen') or state.get('focusActive') or state.get('menuOpen'):return
        job=self.pending.popleft();kind=job['kind'];job['started']=time.monotonic()
        if pressure or time.monotonic()<self.model_retry_after:
            self._finish(job,state,source='system_pressure_policy' if pressure else 'model_unavailable_policy');return
        model_state={'event':EVENTS[kind][0],'user_context':'normal'}
        if job['detail'] is not None:model_state['observation']=job['detail']
        if kind in ['cpu','ram'] and self.processes:model_state['largest_consumer']=(self.processes['top_cpu' if kind=='cpu' else 'top_ram'] or [None])[0]
        schema=TASK_QUESTIONS if kind=='task' else DISK_QUESTIONS if kind=='disk' else NETWORK_QUESTIONS if kind=='network' else QUESTIONS
        self.inflight=job
        try:accepted=self.classifier.submit(job['id'],model_state,schema)
        except OSError:accepted=False
        if not accepted:
            self.classifier.close('unavailable');self.model_retry_after=time.monotonic()+300
            self.inflight=None;self._finish(job,state,source='model_unavailable_policy')
    def collect(self,state):
        now=time.monotonic()
        events=state.get('events',[])
        if self.seen is None:self.seen=max((x.get('at',0) for x in events),default=0)
        else:
            for e in events:
                if e.get('at',0)>self.seen and e.get('kind')=='connection':self.decide('connection',state)
            self.seen=max([self.seen]+[x.get('at',0) for x in events])
        current=files(self.downloads)
        for name,stamp in current.items():
            if self.previous_files.get(name)!=stamp:self.changing[name]=(stamp,now)
        for name,(stamp,started) in list(self.changing.items()):
            if name not in current:self.changing.pop(name,None)
            elif current[name]==stamp and now-started>=6:
                if now-self.cooldowns.get('download',0)>10:self.decide('download',state);self.cooldowns['download']=now
                self.changing.pop(name,None)
        self.previous_files=current
        sample=cpu_sample();total=sample[0]-self.previous_cpu[0];idle=sample[1]-self.previous_cpu[1];self.previous_cpu=sample
        cpu=100*(1-idle/total) if total>0 else 0;ram=ram_percent()
        for kind,high in [('cpu',cpu>=95),('ram',ram>=90)]:
            if not high:
                self.high_since.pop(kind,None)
                if kind in self.resource_notified and getattr(self,'history',None):self.history.recover(kind)
                self.resource_notified.discard(kind)
                self.queue=deque((x for x in self.queue if x['kind']!=kind),maxlen=4)
                if getattr(self,'pending',None):self.pending=deque((x for x in self.pending if x['kind']!=kind),maxlen=4)
                if getattr(self,'inflight',None) and self.inflight['kind']==kind:self.event_versions[kind]=None
                continue
            self.high_since.setdefault(kind,now)
            if now-self.high_since[kind]>=60 and kind not in self.resource_notified and now-self.cooldowns.get(kind,0)>=300:
                self.decide(kind,state);self.cooldowns[kind]=now;self.resource_notified.add(kind)
        return {'cpu':round(cpu,1),'ram':round(ram,1)}
    def deliver(self,state):
        now=time.time()
        while self.queue and self.queue[0]['expires']<now:
            item=self.queue.popleft()
            if getattr(self,'history',None):self.history.stage(item.get('history_id'),'expired')
        if not self.queue or state.get('fullscreen') or state.get('focusActive') or state.get('menuOpen') or now-self.last_shown<8:return
        while self.shown_times and now-self.shown_times[0]>=300:self.shown_times.popleft()
        if len(self.shown_times)>=3:return
        while self.queue and now-self.kind_shown.get(delivery_key(self.queue[0]),0)<60:
            item=self.queue.popleft()
            if getattr(self,'history',None):self.history.stage(item.get('history_id'),'quiet')
        if not self.queue:return
        item=self.queue[0]
        accepted=shell_call('Present',json.dumps(item,ensure_ascii=False))
        if accepted is True:
            if getattr(self,'history',None):self.history.stage(item.get('history_id'),'shown')
            self.queue.popleft();self.last_shown=now;self.shown_times.append(now);self.kind_shown[delivery_key(item)]=now;self.last_delivery={'at':now,'kind':item['kind']};LOG.info(json.dumps({'delivered':item['kind']}))
    def run(self):
        LOG.info('Lightweight monitoring started; Laya loads only when needed')
        while self.running:
            previous_muted=set(self.preferences['muted_kinds']);self.preferences=preferences.read()
            for unmuted in previous_muted-set(self.preferences['muted_kinds']):
                self.resource_notified.discard(unmuted);self.cooldowns.pop(unmuted,None)
                if unmuted=='disk':self.disk_watch.episodes.clear();self.disk_watch.last_sample=None
                if unmuted=='service':
                    for episode in self.service_watch.episodes.values():episode['reported']=False
            if not self.preferences['enabled']:break
            raw=shell_call('GetState')
            try:state=json.loads(raw) if raw else {}
            except (TypeError,json.JSONDecodeError):state={}
            self.processes=self.observer.sample(state.get('foregroundPid',0))
            if self.observer.generation!=self.task_generation:
                self.task_generation=self.observer.generation
                tasks=self.task_watch.update(self.observer.current_processes)
                if tasks:self.decide('task',state,{**tasks[-1],'count':len(tasks)})
            service_events=self.service_watch.update()
            if service_events:
                event=service_events[0].copy()
                if len(service_events)>1:event['name']+=f" та ще {len(service_events)-1}"
                self.decide('service',state,event)
            disk_events,disk_recovered=self.disk_watch.update()
            if disk_recovered:
                self.history.recover('disk');self.queue=deque((x for x in self.queue if x['kind']!='disk'),maxlen=4)
            if disk_events:self.decide('disk',state,{**disk_events[0],'count':len(disk_events)})
            network_event=self.network_watch.update()
            if network_event:self.decide('network',state,network_event)
            metrics=self.collect(state);self.metrics=metrics
            self.process_model(state)
            if raw:self.deliver(state)
            status_write({'active':True,'heartbeat':time.time(),'model':'Laya multilingual','device':'cpu','inferences':self.inferences,'last_decision':self.last_decision,'last_delivery':self.last_delivery,'queue_length':len(self.queue),'pending_classifications':len(self.pending)+(1 if self.inflight else 0),'classifier':self.classifier.status(),'preferences':self.preferences,'network_monitor':self.network_watch.snapshot,'bridge_ready':state.get('modelBridge') is True,'metrics':metrics,'process_monitor':self.processes,'last_recommendation':self.last_recommendation,'music_scene':self.music.status(),'optimization_mode':'recommendations_only','automatic_actions':False,'long_tasks':self.task_watch.status(),'watched_services':self.service_watch.status(),'disk_monitor':self.disk_watch.status(),'history':self.history.recent(),'history_storage_ok':self.history.storage_ok})
            time.sleep(2)
        self.classifier.close('disabled');self.preferences=preferences.read()
        status_write({'active':False,'heartbeat':time.time(),'model':'Laya multilingual','inferences':self.inferences,'history':self.history.recent(),'preferences':self.preferences,'classifier':self.classifier.status()})

if __name__=='__main__':
    m=Monitor()
    signal.signal(signal.SIGTERM,lambda *_:setattr(m,'running',False))
    signal.signal(signal.SIGINT,lambda *_:setattr(m,'running',False))
    m.run()
