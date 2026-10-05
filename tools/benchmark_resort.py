"""Measure the owned Lively WebView2 process tree, not all WebView2 apps."""
import argparse,json,time,subprocess,urllib.request
from pathlib import Path
import psutil
p=argparse.ArgumentParser();p.add_argument('label');p.add_argument('--seconds',type=int,default=30);a=p.parse_args()
# Lively switches players asynchronously. Let the new page report fresh counters
# before discovering its process tree and taking the first playback snapshot.
time.sleep(5)
expected='atlas' if a.label.startswith('atlas') else 'still' if a.label.startswith('still') else 'video'
expectedState='editing' if a.label=='runtime-v3-editing' else 'done' if a.label=='runtime-v3-coffee' else None
for attempt in range(25):
    try:
        status=json.load(urllib.request.urlopen('http://127.0.0.1:18765/bench-metrics',timeout=1))
        if status.get('format')==expected and ('state' in status)==a.label.startswith('runtime') and (expectedState is None or status.get('state')==expectedState):break
    except OSError:pass
    time.sleep(1)
else:raise RuntimeError('New benchmark page has not reported matching telemetry')
players=[p for p in psutil.process_iter(['name']) if p.info['name'].lower()=='lively.player.webview2.exe']
if len(players)!=1:raise RuntimeError('Expected exactly one Lively player; do not disturb another wallpaper owner')
root=players[0];processes=[root]+root.children(recursive=True)
# Include the local event/coverage host and the necessary Lively core service.
# Identify our host by its loopback listener, without logging command lines.
hostIds={c.pid for c in psutil.net_connections(kind='tcp') if c.pid and c.status=='LISTEN' and c.laddr.ip=='127.0.0.1' and c.laddr.port==18765}
core=[proc for proc in psutil.process_iter(['name']) if proc.info['name'].lower()=='lively.exe']
processes+=core+[psutil.Process(pid) for pid in hostIds]
processes=list({proc.pid:proc for proc in processes}.values())
def totals():
    cpu=0;ram=0
    for proc in processes:
        try:t=proc.cpu_times();cpu+=t.user+t.system;ram+=proc.memory_info().rss
        except psutil.NoSuchProcess:pass
    return cpu,ram
out=Path(__file__).resolve().parents[1]/'docs/evidence/resort';out.mkdir(parents=True,exist_ok=True)
gpuFile=out/(a.label+'-gpu.json')
gpuProc=subprocess.Popen(['powershell','-NoProfile','-File',str(Path(__file__).with_name('measure_resort_gpu.ps1')),'-ProcessIds',','.join(str(p.pid) for p in processes),'-Seconds',str(a.seconds),'-OutputFile',str(gpuFile)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
try:playbackBefore=json.load(urllib.request.urlopen('http://127.0.0.1:18765/bench-metrics',timeout=1))
except OSError:playbackBefore={}
c0,_=totals();start=time.monotonic();rss=[]
for _ in range(a.seconds):time.sleep(1);rss.append(totals()[1])
c1,_=totals();elapsed=time.monotonic()-start
gpuExit=gpuProc.wait(timeout=15)
try:playback=json.load(urllib.request.urlopen('http://127.0.0.1:18765/bench-metrics',timeout=1))
except OSError:playback={}
assert root.is_running() and playback.get('format')==playbackBefore.get('format') and ('state' in playback)==('state' in playbackBefore),'Player changed while measuring; discard this run'
assert expectedState is None or playback.get('state')==expectedState,'Task state changed during measurement; discard this run'
playbackSeconds=playback.get('clock',0)-playbackBefore.get('clock',0)
observedFps=((playback.get('totalVideoFrames',0)-playbackBefore.get('totalVideoFrames',0)) if playback.get('format')=='video' else (playback.get('frames',0)-playbackBefore.get('frames',0)))/playbackSeconds if playbackSeconds>0 else 0
assert observedFps>=0,'Player changed while measuring; discard this run'
result={'label':a.label,'gpuCounterExit':gpuExit,'seconds':elapsed,'cpuPercentWholePC':(c1-c0)/elapsed/psutil.cpu_count()*100,'cpuPercentOneCore':(c1-c0)/elapsed*100,'meanRssMiB':sum(rss)/len(rss)/1048576,'peakRssMiB':max(rss)/1048576,'pids':[p.pid for p in processes],'hostPids':sorted(hostIds),'playbackBefore':playbackBefore,'playback':playback,'observedPlaybackFps':observedFps,'scope':'Lively WebView2 wrapper/descendants, Lively core, and loopback event host. RSS sums shared mappings. Video fps counts decoded frames; atlas fps counts rAF draw submissions, not physical display presents. GPU/VRAM are Windows per-process counters.'}
out=Path(__file__).resolve().parents[1]/'docs/evidence/resort';out.mkdir(parents=True,exist_ok=True);(out/(a.label+'.json')).write_text(json.dumps(result,indent=2));print(json.dumps(result))
