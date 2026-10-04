"""NetworkManager's connectivity result, debounced without custom network probes."""
import subprocess,time,os

def connectivity():
    try:
        r=subprocess.run(['nmcli','-t','-f','STATE,CONNECTIVITY','general'],capture_output=True,text=True,timeout=2,env={**os.environ,'LC_ALL':'C'})
        if r.returncode:return None
        state,check=r.stdout.strip().split(':',1)
        if check=='full':return 'online'
        if state in ['disconnected','asleep'] or check in ['none','limited','portal']:return 'offline'
    except (OSError,ValueError,subprocess.TimeoutExpired):pass
    return None

class NetworkWatch:
    def __init__(self):self.last_sample=None;self.stable=None;self.candidate=None;self.since=0;self.snapshot={'state':'unknown'}
    def update(self,now=None,value=None,force=False):
        now=time.monotonic() if now is None else now
        if not force and self.last_sample is not None and now-self.last_sample<5:return None
        self.last_sample=now;value=connectivity() if value is None else value
        if value not in ['online','offline']:
            self.candidate=None;self.snapshot={'state':'unknown'};return None
        self.snapshot={'state':value,'source':'NetworkManager connectivity check'}
        if self.stable is None:self.stable=value;self.candidate=None;return None
        if value==self.stable:self.candidate=None;return None
        if value!=self.candidate:self.candidate=value;self.since=now;return None
        if now-self.since<10:return None
        self.stable=value;self.candidate=None
        return {'state':value}
