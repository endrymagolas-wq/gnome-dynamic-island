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
finally:server.shutdown();server.server_close()
print('PASS loopback host, authenticated events, priority expiry, multiwindow coverage and path containment')
