"""On-demand short resource snapshot, available without the model or daemon."""
import time
from pathlib import Path
from process_observer import ProcessObserver,recommendation

def cpu_sample():
    values=[int(x) for x in Path('/proc/stat').read_text().splitlines()[0].split()[1:9]]
    return sum(values),values[3]+values[4]

def ram_percent():
    m={x.split(':')[0]:int(x.split()[1]) for x in Path('/proc/meminfo').read_text().splitlines()}
    return 100*(1-m['MemAvailable']/m['MemTotal'])

def diagnose(foreground_pid=0):
    observer=ProcessObserver();observer.sample(foreground_pid,force=True);first=cpu_sample();start=time.monotonic();time.sleep(.4)
    snapshot=observer.sample(foreground_pid,force=True);last=cpu_sample();delta=last[0]-first[0]
    cpu=100*(1-(last[1]-first[1])/delta) if delta>0 else 0;ram=ram_percent();psi=snapshot['pressure_avg10'] if snapshot else {}
    pressure=cpu>=85 or ram>=85 or (psi.get('cpu') or 0)>=20 or (psi.get('memory') or 0)>=5 or (psi.get('io') or 0)>=10
    kind='cpu' if cpu>=85 or (psi.get('cpu') or 0)>=20 else 'ram'
    advice=recommendation(kind,snapshot) if pressure else None
    if (psi.get('io') or 0)>=10 and cpu<85 and ram<85:advice={'advice':'Диск зайнятий; перевір копіювання та завантаження'}
    return {'summary':'Є тиск на ресурси' if pressure else 'Зараз система має запас ресурсів','cpu':round(cpu,1),'ram':round(ram,1),'top_cpu':(snapshot.get('top_cpu') or [None])[0] if snapshot else None,'top_ram':(snapshot.get('top_ram') or [None])[0] if snapshot else None,'advice':advice['advice'] if advice else 'Помітного тиску зараз не видно' if not pressure else 'Перевір системний монітор','observed_at':time.time(),'window_seconds':round(time.monotonic()-start,2),'pressure_avg10':psi,'automatic_action':False}
