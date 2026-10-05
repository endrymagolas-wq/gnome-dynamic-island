"""Explicit scene-state adapter for any local program (not activity inference)."""
import argparse,json,os,urllib.request
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('state',choices=['starting','editing','testing','failed','permission','done','working','browsing','idle']);a=p.parse_args()
c=json.loads((Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'ResortIsland/connection.json').read_text())
if not c['url'].startswith('http://127.0.0.1:'):raise ValueError('Loopback only')
r=urllib.request.Request(c['url'],data=json.dumps({'state':a.state}).encode(),headers={'Authorization':'Bearer '+c['token'],'Content-Type':'application/json'})
with urllib.request.urlopen(r,timeout=1) as response:assert response.status==200
