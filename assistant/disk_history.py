"""Small read-only disk sampler and private bounded event journal."""
import json,math,os,shutil,time,uuid
from pathlib import Path
GiB=1024**3
KINDS={'connection','download','cpu','ram','task','service','disk','network'}
STAGES={'queued','shown','recovered','expired','superseded','quiet'}

def clean(value,limit):
    return ''.join(c for c in str(value) if c.isprintable())[:limit]

class History:
    def __init__(self,path):
        self.path=Path(path);self.entries=[];self.storage_ok=True
        try:
            if self.path.stat().st_size<=65536:
                rows=json.loads(self.path.read_text())
                if isinstance(rows,list):
                    for row in rows[-60:]:
                        if not isinstance(row,dict) or row.get('kind') not in KINDS or row.get('stage') not in STAGES:continue
                        at=row.get('at')
                        if isinstance(at,bool) or not isinstance(at,(int,float)) or not math.isfinite(at) or at<0:continue
                        self.entries.append({'id':clean(row.get('id',''),40),'at':at,'kind':row['kind'],'title':clean(row.get('title',''),48),'message':clean(row.get('message',''),72),'advice':clean(row.get('advice',''),72),'stage':row['stage']})
        except (OSError,ValueError,TypeError):pass
    def save(self):
        self.entries=self.entries[-60:]
        try:
            temporary=self.path.with_suffix('.tmp')
            fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
            with os.fdopen(fd,'w') as f:
                os.fchmod(f.fileno(),0o600);json.dump(self.entries,f,ensure_ascii=False)
            temporary.replace(self.path);self.storage_ok=True
        except OSError:self.storage_ok=False
    def record(self,item):
        key=str(uuid.uuid4())
        self.entries.append({'id':key,'at':time.time(),'kind':item['kind'],'title':clean(item['title'],48),'message':clean(item['message'],72),'advice':clean(item.get('advice') or '',72),'stage':'queued'})
        self.save();return key
    def stage(self,key,stage):
        if stage not in STAGES:return
        for row in reversed(self.entries):
            if row['id']==key and row['stage']!=stage:row['stage']=stage;self.save();return
    def recover(self,kind):
        for row in reversed(self.entries):
            if row['kind']==kind:
                if row['stage']!='recovered':row['stage']='recovered';self.save()
                return
    def recent(self):return self.entries[-5:][::-1]

class DiskWatch:
    def __init__(self,targets=None):
        self.targets=targets or [('Система',Path('/')),('Домашній диск',Path.home())]
        self.last_sample=None;self.snapshot=[];self.episodes=set()
    def update(self,now=None,force=False):
        now=time.monotonic() if now is None else now
        if not force and self.last_sample is not None and now-self.last_sample<30:return [],False
        self.last_sample=now;rows=[];seen=set();events=[];recovered=False
        for label,path in self.targets[:2]:
            try:
                device=path.stat().st_dev
                if device in seen:continue
                usage=shutil.disk_usage(path)
                if usage.total<=0 or usage.free<0:continue
                seen.add(device);percentage=100*usage.free/usage.total
                low=usage.free<5*GiB or (percentage<=5 and usage.free<20*GiB)
                healthy=usage.free>=7*GiB and (percentage>7 or usage.free>=25*GiB)
                if healthy and device in self.episodes:self.episodes.remove(device);recovered=True
                if low and device not in self.episodes:
                    self.episodes.add(device)
                    events.append({'name':label,'free_gib':round(usage.free/GiB,1),'free_percent':round(percentage,1)})
                rows.append({'name':label,'free_gib':round(usage.free/GiB,1),'free_percent':round(percentage,1),'low':device in self.episodes,'available':True})
            except OSError:
                rows.append({'name':label,'available':False})
        self.snapshot=rows
        # Missing filesystem readings are never treated as recovery.
        return events,recovered and not self.episodes
    def status(self):return {'filesystems':self.snapshot,'sample_seconds':30,'automatic_cleanup':False}
