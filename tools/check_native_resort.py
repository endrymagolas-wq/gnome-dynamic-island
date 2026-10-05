"""Opt-in live Lively checks. Requires the runtime benchmark library entry."""
import argparse,json,os,subprocess,sys,time,urllib.request
import hashlib,datetime
from pathlib import Path
root=Path(__file__).resolve().parents[1];out=root/'docs/evidence/resort';out.mkdir(parents=True,exist_ok=True)
cli=Path(os.environ['LOCALAPPDATA'])/'ResortIsland/lively-cli/Livelycu.exe'
p=argparse.ArgumentParser();p.add_argument('mode',choices=['controls','reactions']);args=p.parse_args()
def command(*items):subprocess.run([str(cli),*items],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
def metrics():return json.load(urllib.request.urlopen('http://127.0.0.1:18765/bench-metrics',timeout=2))
def pair():
 time.sleep(2);before=metrics();time.sleep(3);return before,metrics()
if args.mode=='controls':
 report={}
 try:
  command('app','--play','false');a,b=pair();assert b['paused'] and b['videoPaused'] and b['totalVideoFrames']<=a['totalVideoFrames']+1;report['manualPause']=[a,b]
  command('app','--play','true');command('setprop','--property','water=false');a,b=pair();assert b['format']=='still' and b['videoPaused'] and b['totalVideoFrames']<=a['totalVideoFrames']+1;report['waterOff']=[a,b]
  command('setprop','--property','water=true');command('setprop','--property','quality=1');a,b=pair();assert b['videoWidth']==1280 and b['totalVideoFrames']>a['totalVideoFrames']+30;report['720p']=[a,b]
  command('setprop','--property','quality=2');a,b=pair();assert b['format']=='still' and b['videoPaused'] and b['totalVideoFrames']<=a['totalVideoFrames']+1;report['qualityOff']=[a,b]
 finally:command('app','--play','true');command('setprop','--property','water=true');command('setprop','--property','quality=0')
else:
 meta=json.loads((root/'wallpaper/assets/scene.json').read_text());report={}
 events=[('starting',{'hook_event_name':'UserPromptSubmit'}),*[(f'editing-{i}',{'hook_event_name':'PreToolUse','tool_name':'Edit'}) for i in range(1,5)],('testing',{'hook_event_name':'PreToolUse','tool_name':'Bash','tool_input':{'command':'pytest -q'}}),('failed',{'hook_event_name':'PostToolUseFailure','tool_name':'Bash','tool_input':{'command':'pytest -q'}}),('permission',{'hook_event_name':'PermissionRequest'}),('done',{'hook_event_name':'Stop'}),('browsing',None),('working',None),('idle',None)]
 for label,payload in events:
  state=label.split('-')[0]
  if payload:subprocess.run([sys.executable,str(root/'assistant/claude_hook.py')],input=json.dumps(payload),text=True,check=True)
  else:subprocess.run([sys.executable,str(root/'wallpaper/emit.py'),state],check=True)
  target=meta['targets'].get(state,meta['targets']['desk']);deadline=time.monotonic()+35
  while time.monotonic()<deadline:
   current=metrics()
   stageReady=state!='editing' or current.get('stage')==int(label.split('-')[1])
   if current.get('state')==state and stageReady and all(abs(a-b)<.001 for a,b in zip(current.get('position',[]),target)) and len(current.get('position',[]))==3:break
   time.sleep(.5)
  else:raise AssertionError((label,'Native scene did not reach target',current,target))
  if state=='editing':assert current['stage']==int(label.split('-')[1])
  if state=='failed':
   time.sleep(1.2);current=metrics();assert current.get('smokeVisiblePixels',0)>100,'Native smoke was fully occluded or not drawn'
  report[label]=current
  imagePath=out/(label+'.jpg');requested=time.time();command('screenshot','--file',str(imagePath))
  deadline=time.monotonic()+10
  while time.monotonic()<deadline:
   if imagePath.exists() and imagePath.stat().st_mtime>=requested-1 and imagePath.stat().st_size>10000:break
   time.sleep(.2)
  else:raise AssertionError((label,'Native screenshot was not refreshed'))
 report['method']='Synthetic Claude hook payloads through the real Windows transport and native Lively player. No paid model call; test commands were not executed.'
report['assets']={name:hashlib.sha256((root/'wallpaper/assets'/name).read_bytes()).hexdigest() for name in ['scene.json','character.png','water-1080.mp4']}
report['recordedAt']=datetime.datetime.now(datetime.timezone.utc).isoformat()
(out/('native-'+args.mode+'.json')).write_text(json.dumps(report,indent=2,ensure_ascii=False))
print('PASS native '+args.mode)
