import importlib.util, sys, json, threading, urllib.request, urllib.error, time
from pathlib import Path
root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('resort_host',root/'wallpaper/server.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
assert m.covered((0,0,100,100),[(0,0,50,100),(50,0,100,100)])
assert not m.covered((0,0,100,100),[(0,0,49,100),(50,0,100,100)])
assert m.publish('starting',now=100);assert not m.publish('idle','desktop',now=101);assert m.publish('idle','desktop',now=281)
server=m.ThreadingHTTPServer(('127.0.0.1',0),m.Handler);server.token='test-only';threading.Thread(target=server.serve_forever,daemon=True).start();url=f'http://127.0.0.1:{server.server_port}'
try:
 for state in m.STATES:
  req=urllib.request.Request(url+'/event',data=json.dumps({'state':state}).encode(),headers={'Authorization':'Bearer test-only'})
  assert urllib.request.urlopen(req).status==200
  status=json.load(urllib.request.urlopen(url+'/events'));assert status['state']==state
 for path in ['/../assistant/claude_hook.py','/wallpaper/../../README.md']:
  try:urllib.request.urlopen(url+path);raise AssertionError('Path escaped wallpaper')
  except urllib.error.HTTPError as e:assert e.code==404
 req=urllib.request.Request(url+'/event',data=b'{"state":"failed"}')
 try:urllib.request.urlopen(req);raise AssertionError('Missing token accepted')
 except urllib.error.HTTPError as e:assert e.code==403
 telemetry={'format':'video','state':'done','position':[-.61,-2.12,.64],'seated':True,'transition':None,
            'ambient':'yawn','actorRect':[128,2560,128,160],'restTime':33,'actorVisiblePixels':12000,
            'lighting':{'mode':'auto','a':'morning','b':'day','mix':.5,'decoderCount':2,'clockDelta':.02},
            'privateText':'must not be retained'}
 req=urllib.request.Request(url+'/bench-metrics',data=json.dumps(telemetry).encode(),headers={'Origin':url})
 assert urllib.request.urlopen(req).status==200
 recorded=json.load(urllib.request.urlopen(url+'/bench-metrics'))
 assert recorded.get('lighting')==telemetry['lighting'] and recorded.get('actorRect')==telemetry['actorRect'],'New lighting/actor telemetry was dropped'
 assert recorded.get('ambient')=='yawn' and recorded.get('seated') is True and 'privateText' not in recorded
 telemetry['lighting']['mode']='unrecognized application text'
 req=urllib.request.Request(url+'/bench-metrics',data=json.dumps(telemetry).encode(),headers={'Origin':url})
 try:urllib.request.urlopen(req);raise AssertionError('Unbounded lighting text accepted')
 except urllib.error.HTTPError as e:assert e.code==400
finally:server.shutdown();server.server_close()
print('PASS loopback host, authenticated events, priority expiry, multiwindow coverage and path containment')
