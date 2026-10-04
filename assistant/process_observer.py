"""Read-only same-user process samples. Never reads cmdline/env or changes processes."""
import os,re,time
from pathlib import Path

SYSTEM={'gnome-shell','systemd','dbus-daemon','dbus-broker','pipewire','wireplumber','pulseaudio','gdm','Xwayland','Xorg','gnome-session','gnome-session-b','shairport-sync'}
BROWSERS={'chrome','chromium','firefox','Web Content','Isolated Web Co','brave','msedge'}
EDITORS={'codex','Codex','chatgpt','ChatGPT','claude','Claude','claude-desktop','Antigravity','antigravity','code','Code','electron','Electron','gedit','Text Editor','vim','nvim','emacs'}
TERMINALS={'bash','zsh','fish','sh','gnome-terminal-','kgx','konsole','kitty','alacritty','sshd','tmux'}
BUILDS={'gcc','g++','cc1','cc1plus','clang','clang++','rustc','cargo','make','ninja','cmake','ld','lld','javac'}

def clean_name(name):return re.sub(r'[^\w .+@-]','',name)[:24] or 'процес'

def parse_stat(text,page_size=4096):
    first=text.index('(');last=text.rindex(')');pid=int(text[:first].strip());name=text[first+1:last];parts=text[last+2:].split()
    return {'pid':pid,'name':clean_name(name),'ppid':int(parts[1]),'ticks':int(parts[11])+int(parts[12]),'start':int(parts[19]),'rss_mib':max(0,int(parts[21]))*page_size/1048576}

def role(proc,processes,foreground_pid,self_pid):
    if proc['pid']==self_pid:return 'assistant'
    if proc['name'] in SYSTEM:return 'system'
    if proc['name'] in BROWSERS:return 'browser'
    if proc['name'] in EDITORS:return 'editor'
    if proc['name'] in TERMINALS:return 'terminal'
    if proc['name'] in BUILDS:return 'build'
    current=proc;seen=set()
    for _ in range(32):
        if current['pid']==foreground_pid:return 'active'
        if current['pid'] in seen:break
        seen.add(current['pid']);current=processes.get(current['ppid'])
        if not current:break
        if current['pid']==self_pid:return 'assistant'
        if current['name'] in BROWSERS:return 'browser'
        if current['name'] in EDITORS:return 'editor'
        if current['name'] in TERMINALS:return 'terminal'
        if current['name'] in BUILDS:return 'build'
    # Unknown is not evidence that stopping this process is safe.
    return 'unknown'

def pressure(root=Path('/proc')):
    result={}
    for kind in ['cpu','memory','io']:
        result[kind]=None
        try:
            line=next(x for x in (root/'pressure'/kind).read_text().splitlines() if x.startswith('some '))
            result[kind]=float(dict(x.split('=') for x in line.split()[1:])['avg10'])
        except (OSError,ValueError,StopIteration,KeyError):pass
    return result

class ProcessObserver:
    def __init__(self,root=Path('/proc')):
        self.root=root;self.previous={};self.previous_total=None;self.last_sample=0;self.snapshot=None;self.current_processes={};self.generation=0
        self.page_size=os.sysconf('SC_PAGE_SIZE');self.uid=os.getuid();self.self_pid=os.getpid()
    def sample(self,foreground_pid=0,force=False):
        now=time.monotonic()
        if not force and self.snapshot is not None and now-self.last_sample<10:return self.snapshot
        try:
            total=sum(int(x) for x in (self.root/'stat').read_text().splitlines()[0].split()[1:9])
        except (OSError,ValueError):return self.snapshot
        delta=total-self.previous_total if self.previous_total is not None else 0
        processes={}
        try:
            with os.scandir(self.root) as entries:
                for count,entry in enumerate(entries):
                    if count>=8192:break
                    if not entry.name.isdecimal():continue
                    try:
                        if entry.stat(follow_symlinks=False).st_uid!=self.uid:continue
                        p=parse_stat((self.root/entry.name/'stat').read_text(),self.page_size)
                        prior=self.previous.get((p['pid'],p['start']))
                        p['cpu_total_percent']=100*max(0,p['ticks']-prior)/delta if prior is not None and delta>0 else 0
                        processes[p['pid']]=p
                    except (OSError,ValueError,IndexError):continue
        except OSError:return self.snapshot
        self.current_processes=processes;self.generation+=1
        groups={}
        for p in processes.values():
            r=role(p,processes,int(foreground_pid or 0),self.self_pid);key=(p['name'],r)
            g=groups.setdefault(key,{'name':p['name'],'role':r,'protected':r!='unknown','auto_stop_allowed':False,'count':0,'cpu_total_percent':0,'rss_mib':0})
            g['count']+=1;g['cpu_total_percent']+=p['cpu_total_percent'];g['rss_mib']+=p['rss_mib']
        values=list(groups.values())
        for g in values:g['cpu_total_percent']=round(g['cpu_total_percent'],1);g['rss_mib']=round(g['rss_mib'])
        self.snapshot={'sample_at':time.time(),'cpu_basis':'percent of total machine CPU capacity','memory_basis':'sum of RSS; shared pages may be counted more than once','foreground_known':bool(foreground_pid),'top_cpu':sorted(values,key=lambda x:x['cpu_total_percent'],reverse=True)[:5],'top_ram':sorted(values,key=lambda x:x['rss_mib'],reverse=True)[:5],'pressure_avg10':pressure(self.root),'actions_enabled':False}
        self.previous={(p['pid'],p['start']):p['ticks'] for p in processes.values()};self.previous_total=total;self.last_sample=now
        return self.snapshot

ADVICE={'system':'Перевір службу; не зупиняй навмання','browser':'Перевір вкладки й розширення','editor':'Перевір задачі й розширення редактора','terminal':'Перевір задачі в терміналі','build':'Дочекайся завершення збірки','active':'Це активна програма; перевір її задачі','assistant':'Помічник теж використовує ресурси','unknown':'Перевір, чи цей процес тобі потрібний'}

def recommendation(kind,snapshot):
    if not snapshot:return None
    candidates=snapshot.get('top_cpu' if kind=='cpu' else 'top_ram',[])
    if not candidates:return None
    top=candidates[0]
    if kind=='cpu' and top['cpu_total_percent']<1:return None
    ram=(f"{top['rss_mib']/1024:.1f}".replace('.',',')+' ГіБ') if top['rss_mib']>=1024 else f"{top['rss_mib']} МіБ"
    message=f"{top['name']} · {top['cpu_total_percent']:g}% усіх CPU" if kind=='cpu' else f"{top['name']} · RAM ≈ {ram}"
    return {'message':message,'advice':ADVICE.get(top['role'],ADVICE['unknown']),'process':top,'automatic_action':False}
